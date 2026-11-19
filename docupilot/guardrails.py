"""Guardrails: block prompt injection, refuse off-topic questions, redact personal data.

Pure rules (no AI calls), so they are fast, free and testable offline.
"""
from __future__ import annotations

import re

INJECTION_PATTERNS = [
    r"ignore (all |any |the |your )?(previous|prior|above|earlier|system) (instructions|prompts?|rules)",
    r"disregard (all |any |the )*(previous|prior|above|your|these)? ?(instructions|rules)",
    r"(reveal|show|print|repeat|output) (me )?(your|the) (system )?(prompt|instructions)",
    r"you are now\b",
    r"\bdeveloper mode\b|\bDAN\b|\bjailbreak\b",
    r"act as (an? )?(admin|administrator|root|unrestricted)",
    r"pretend (you have no|there are no) (rules|restrictions)",
    r"(show|dump|list|give me) (all )?(the )?(employee|salary|password|credential)s?.*(all|every)",
]
_INJECTION_RE = re.compile("|".join(INJECTION_PATTERNS), re.I)

OFF_TOPIC_RE = re.compile(
    r"\b(recipe|cook|weather|forecast|joke|poem|song|lyrics|horoscope|cricket score|football|"
    r"movie|stock price|bitcoin|crypto|election|write (me )?(a|an) (story|essay|code|script))\b",
    re.I,
)

HR_IT_RE = re.compile(
    r"\b(leave|holiday|sick|casual|earned|maternity|paternity|balance|employee|manager|department|"
    r"email|phone|contact|location|join|ticket|it|laptop|vpn|password|mfa|access|licen[cs]e|support|"
    r"hr|policy|payroll)\b|\b(E\d{3,6}|IT-\d{3,6})\b",
    re.I,
)

REFUSAL_INJECTION = (
    "I can't follow instructions that try to change my rules or reveal internal details. "
    "I can answer HR and IT questions, for example: \"How many leave days does E102 have left?\""
)
REFUSAL_OFF_TOPIC = (
    "I can only answer HR and IT questions (leave, employee details, IT tickets and the company "
    "policies in the knowledge base)."
)

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_PHONE_RE = re.compile(r"(?<!\w)\+?\d[\d\s-]{7,}\d(?!\w)")


def is_injection(question: str) -> bool:
    return bool(_INJECTION_RE.search(question or ""))


def is_off_topic(question: str) -> bool:
    """Off topic = matches a known off-topic subject and no HR/IT term."""
    return bool(OFF_TOPIC_RE.search(question or "")) and not HR_IT_RE.search(question or "")


def is_hr_it(question: str) -> bool:
    return bool(HR_IT_RE.search(question or ""))


def redact(text: str) -> str:
    """Hide email addresses and phone numbers in any answer text."""
    text = _EMAIL_RE.sub("[email redacted]", text or "")
    return _PHONE_RE.sub(lambda m: "[phone redacted]" if sum(c.isdigit() for c in m.group()) >= 9 else m.group(), text)
