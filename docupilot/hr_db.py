"""Read-only access to the HR / IT Postgres database.

Only fixed, parameterised SELECT statements live here; there is no way to run free-form SQL.
Every connection is opened read-only with a statement timeout, IDs are validated before they
reach the database, and results are capped. The MCP server (mcp_server.py) is the only caller.
"""
from __future__ import annotations

import datetime as dt
import decimal
import re
from pathlib import Path
from typing import Any, Protocol

EMPLOYEE_ID_RE = re.compile(r"^E\d{3,6}$")
TICKET_ID_RE = re.compile(r"^IT-\d{3,6}$")
LEAVE_TYPES = ("earned", "casual", "sick")
TICKET_STATUSES = ("open", "in_progress", "resolved", "closed")
MAX_ROWS = 50
SQL_DIR = Path(__file__).resolve().parent.parent / "hr"


class InvalidInput(ValueError):
    """A tool argument failed validation (bad ID format, unknown leave type…)."""


def normalise_employee_id(value: str) -> str:
    v = (value or "").strip().upper()
    if not EMPLOYEE_ID_RE.match(v):
        raise InvalidInput(f"'{value}' is not a valid employee ID (expected E followed by digits, e.g. E102).")
    return v


def normalise_ticket_id(value: str) -> str:
    v = (value or "").strip().upper()
    if not TICKET_ID_RE.match(v):
        raise InvalidInput(f"'{value}' is not a valid ticket ID (expected IT- followed by digits, e.g. IT-1041).")
    return v


def _check_choice(value: str | None, allowed: tuple[str, ...], what: str) -> str | None:
    if value in (None, "", "any", "all"):
        return None
    v = value.strip().lower().replace(" ", "_")
    if v not in allowed:
        raise InvalidInput(f"Unknown {what} '{value}'. Use one of: {', '.join(allowed)}.")
    return v


def _plain(value: Any) -> Any:
    if isinstance(value, decimal.Decimal):
        return float(value)
    if isinstance(value, (dt.date, dt.datetime)):
        return value.isoformat()
    return value


class Database(Protocol):
    def query(self, sql: str, params: tuple) -> list[dict]: ...


class PostgresDatabase:
    """psycopg 3 connection per query: read-only transaction, 5 s statement timeout."""

    def __init__(self, url: str, timeout_ms: int = 5000):
        if not url:
            raise ValueError("DATABASE_URL is not set")
        self.url, self.timeout_ms = url, timeout_ms

    def query(self, sql: str, params: tuple) -> list[dict]:
        import psycopg
        from psycopg.rows import dict_row

        with psycopg.connect(self.url, row_factory=dict_row, connect_timeout=10,
                             options=f"-c statement_timeout={self.timeout_ms}") as conn:
            conn.read_only = True  # every transaction is READ ONLY: writes fail inside Postgres
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return [{k: _plain(v) for k, v in row.items()} for row in cur.fetchmany(MAX_ROWS)]


class HRRepository:
    """The four questions the agent may ask the database."""

    def __init__(self, db: Database):
        self.db = db

    def get_employee(self, employee_id: str) -> dict:
        eid = normalise_employee_id(employee_id)
        rows = self.db.query(
            "SELECT e.employee_id, e.full_name, e.email, e.phone, e.department, e.job_title, e.location, "
            "e.join_date, e.manager_id, m.full_name AS manager_name "
            "FROM employees e LEFT JOIN employees m ON m.employee_id = e.manager_id "
            "WHERE e.employee_id = %s", (eid,))
        if not rows:
            return {"found": False, "employee_id": eid, "message": f"No employee with ID {eid} exists."}
        return {"found": True, "employee": rows[0]}

    def get_leave_balance(self, employee_id: str, leave_type: str | None = None,
                          leave_year: int | None = None) -> dict:
        eid = normalise_employee_id(employee_id)
        kind = _check_choice(leave_type, LEAVE_TYPES, "leave type")
        year = int(leave_year) if leave_year else dt.date.today().year
        employee = self.db.query("SELECT employee_id, full_name FROM employees WHERE employee_id = %s", (eid,))
        if not employee:
            return {"found": False, "employee_id": eid, "message": f"No employee with ID {eid} exists."}
        sql = ("SELECT leave_type, entitled_days, carried_forward, taken_days, remaining_days "
               "FROM leave_balance_summary WHERE employee_id = %s AND leave_year = %s")
        params: tuple = (eid, year)
        if kind:
            sql += " AND leave_type = %s"
            params += (kind,)
        rows = self.db.query(sql + " ORDER BY leave_type", params)
        return {"found": True, "employee_id": eid, "full_name": employee[0]["full_name"],
                "leave_year": year, "balances": rows,
                "note": "remaining_days = entitled_days + carried_forward - taken_days"}

    def list_it_tickets(self, employee_id: str, status: str | None = None) -> dict:
        eid = normalise_employee_id(employee_id)
        st = _check_choice(status, TICKET_STATUSES + ("unresolved",), "ticket status")
        employee = self.db.query("SELECT employee_id, full_name FROM employees WHERE employee_id = %s", (eid,))
        if not employee:
            return {"found": False, "employee_id": eid, "message": f"No employee with ID {eid} exists."}
        sql = ("SELECT ticket_id, category, title, status, priority, assigned_team, opened_at, updated_at "
               "FROM it_tickets WHERE employee_id = %s")
        params: tuple = (eid,)
        if st == "unresolved":
            sql += " AND status IN ('open', 'in_progress')"
        elif st:
            sql += " AND status = %s"
            params += (st,)
        rows = self.db.query(sql + " ORDER BY opened_at DESC", params)
        return {"found": True, "employee_id": eid, "full_name": employee[0]["full_name"],
                "status_filter": st or "any", "tickets": rows}

    def get_it_ticket(self, ticket_id: str) -> dict:
        tid = normalise_ticket_id(ticket_id)
        rows = self.db.query(
            "SELECT t.ticket_id, t.employee_id, e.full_name AS raised_by, t.category, t.title, t.status, "
            "t.priority, t.assigned_team, t.opened_at, t.updated_at "
            "FROM it_tickets t JOIN employees e ON e.employee_id = t.employee_id WHERE t.ticket_id = %s", (tid,))
        if not rows:
            return {"found": False, "ticket_id": tid, "message": f"No IT ticket with ID {tid} exists."}
        return {"found": True, "ticket": rows[0]}


def init_database(url: str, with_seed: bool = True) -> None:
    """Create the tables (and demo data). Uses a normal read-write connection: admin use only."""
    import psycopg

    files = [SQL_DIR / "schema.sql"] + ([SQL_DIR / "seed.sql"] if with_seed else [])
    with psycopg.connect(url, autocommit=True) as conn:
        for f in files:
            conn.execute(f.read_text(encoding="utf-8"))


if __name__ == "__main__":  # python -m docupilot.hr_db  (reads DATABASE_URL from .env)
    import os

    from dotenv import load_dotenv

    load_dotenv()
    init_database(os.environ["DATABASE_URL"])
    print("HR database ready: employees, leave balances, IT tickets (demo data).")
