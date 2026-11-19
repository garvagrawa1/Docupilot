"""MCP server exposing safe, read-only HR / IT tools backed by Postgres.

Run it on its own (stdio transport, which is what MCP clients such as the DocuPilot agent,
Claude Desktop or the MCP Inspector expect):

    python -m docupilot.mcp_server

It needs DATABASE_URL (ideally pointing at the read-only `docupilot_reader` role from hr/schema.sql).
The tools only run fixed, parameterised SELECT queries (see hr_db.py); there is no raw-SQL tool.
"""
from __future__ import annotations

import os
from typing import Any

from mcp.server.fastmcp import FastMCP

from .hr_db import HRRepository, InvalidInput, PostgresDatabase

TOOL_NAMES = ("get_employee", "get_leave_balance", "list_it_tickets", "get_it_ticket")


def _safe(fn, *args, **kwargs) -> dict[str, Any]:
    try:
        return fn(*args, **kwargs)
    except InvalidInput as e:
        return {"found": False, "error": "invalid_input", "message": str(e)}
    except Exception as e:  # noqa: BLE001 — never leak connection strings or stack traces to the model
        return {"found": False, "error": "database_error",
                "message": f"The HR database could not be queried ({type(e).__name__})."}


def create_server(repo: HRRepository | None = None) -> FastMCP:
    """Build the server. Tests pass a repository backed by a fake database."""
    if repo is None:
        repo = HRRepository(PostgresDatabase(os.getenv("DATABASE_URL", "")))
    server = FastMCP("docupilot-hr")

    @server.tool()
    def get_employee(employee_id: str) -> dict[str, Any]:
        """Look up one employee's profile: name, department, job title, location, join date,
        manager, and work contact details. employee_id looks like 'E102'."""
        return _safe(repo.get_employee, employee_id)

    @server.tool()
    def get_leave_balance(employee_id: str, leave_type: str | None = None,
                          leave_year: int | None = None) -> dict[str, Any]:
        """Leave balance for an employee in a leave year (default: the current year).
        leave_type is optional: 'earned', 'casual' or 'sick'. Each row has entitled_days,
        carried_forward, taken_days and remaining_days."""
        return _safe(repo.get_leave_balance, employee_id, leave_type, leave_year)

    @server.tool()
    def list_it_tickets(employee_id: str, status: str | None = None) -> dict[str, Any]:
        """IT support tickets raised by an employee, newest first. status is optional:
        'open', 'in_progress', 'resolved', 'closed', or 'unresolved' (open + in progress)."""
        return _safe(repo.list_it_tickets, employee_id, status)

    @server.tool()
    def get_it_ticket(ticket_id: str) -> dict[str, Any]:
        """Details and current status of one IT ticket. ticket_id looks like 'IT-1041'."""
        return _safe(repo.get_it_ticket, ticket_id)

    return server


def main() -> None:
    from dotenv import load_dotenv

    load_dotenv()
    create_server().run()  # stdio


if __name__ == "__main__":
    main()
