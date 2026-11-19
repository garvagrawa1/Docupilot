"""Turns an HR/IT question into MCP tool calls, and tool results into a cited answer."""
from __future__ import annotations

import re

from .guardrails import redact

NOT_FOUND_ID = "I need an employee ID (like E102) or an IT ticket ID (like IT-1041) to look that up."
UNCLEAR = (
    "I couldn't tell which HR or IT record you mean. Try including an ID, for example "
    "\"How many leave days does E102 have left?\" or \"What is the status of IT-1041?\""
)


def plan_calls(question: str) -> list[tuple[str, dict]]:
    q = question.lower()
    eid = re.search(r"\bE\d{3,6}\b", question, re.I)
    tid = re.search(r"\bIT-\d{3,6}\b", question, re.I)
    calls: list[tuple[str, dict]] = []
    if tid:
        calls.append(("get_it_ticket", {"ticket_id": tid.group().upper()}))
    if eid:
        emp = eid.group().upper()
        if re.search(r"\b(leave|holiday|sick|casual|earned|balance|left|remaining)\b", q):
            calls.append(("get_leave_balance", {"employee_id": emp}))
        if re.search(r"\b(ticket|tickets|laptop|vpn|it|support|open)\b", q) and not tid:
            calls.append(("list_it_tickets", {"employee_id": emp,
                                              "status": "unresolved" if re.search(r"open|unresolved|pending", q) else None}))
        if not calls:
            calls.append(("get_employee", {"employee_id": emp}))
    return calls


def format_answer(calls: list[tuple[str, dict]], results: list[dict]) -> tuple[str, list[dict]]:
    """Return (answer text, source cards). Every fact is cited against a database source."""
    lines: list[str] = []
    cards: list[dict] = []

    def cite(source: str, snippet: str) -> str:
        cards.append({"n": len(cards) + 1, "label": source, "source": source, "page": None, "found_by": None,
                      "score": None, "origin": "hr_database", "cited": True, "snippet": snippet[:400]})
        return f"[{len(cards)}]"

    for (name, _), res in zip(calls, results):
        if not res.get("found"):
            lines.append(res.get("message") or "No matching record was found.")
            continue
        if name == "get_leave_balance":
            c = cite("hr.leave_balance_summary", str(res.get("balances")))
            for b in res["balances"]:
                lines.append(f"{res['full_name']} ({res['employee_id']}) has {b['remaining_days']:g} "
                             f"{b['leave_type']} leave days left in {res['leave_year']} "
                             f"({b['entitled_days']:g} entitled + {b['carried_forward']:g} carried forward "
                             f"− {b['taken_days']:g} taken) {c}.")
        elif name == "list_it_tickets":
            c = cite("hr.it_tickets", str(res.get("tickets")))
            if not res["tickets"]:
                lines.append(f"{res['full_name']} has no matching IT tickets {c}.")
            for t in res["tickets"]:
                lines.append(f"{t['ticket_id']} ({t['priority']}): {t['title']} — {t['status']} {c}.")
        elif name == "get_it_ticket":
            t = res["ticket"]
            c = cite("hr.it_tickets", str(t))
            lines.append(f"{t['ticket_id']} \"{t['title']}\" raised by {t['raised_by']} is {t['status']} "
                         f"(priority {t['priority']}, team {t['assigned_team']}) {c}.")
        elif name == "get_employee":
            e = res["employee"]
            c = cite("hr.employees", str({k: v for k, v in e.items() if k != "phone"}))
            lines.append(f"{e['full_name']} ({e['employee_id']}) is a {e['job_title']} in {e['department']}, "
                         f"based in {e['location']}, joined {e['join_date']}"
                         + (f", reports to {e['manager_name']}" if e.get("manager_name") else "")
                         + f" {c}.")
    if not lines:
        return NOT_FOUND_ID, []
    return redact("\n".join(lines)), cards
