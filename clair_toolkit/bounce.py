"""Pull the failed address and reason out of a bounce / DSN."""

from __future__ import annotations

import re

from clair_toolkit.util import clip, emails_in

_FINAL = re.compile(r"(?:Final|Original)-Recipient:\s*rfc822;\s*<?([^\s>;]+)>?", re.I)
_ANGLE = re.compile(r"<([^>\s]+@[^>\s]+)>")
_FAILED = re.compile(r"failed recipient[:\s]+<?([^\s>;]+@[^>\s>;]+)>?", re.I)


def parse_bounce(text: str) -> dict:
    text = text or ""
    address = None
    for pattern in (_FINAL, _FAILED):
        match = pattern.search(text)
        if match:
            address = match.group(1).strip("<>").casefold()
            break
    if address is None:
        for match in _ANGLE.finditer(text):
            cand = match.group(1).casefold()
            if cand.startswith("mailer-daemon") or cand.startswith("postmaster"):
                continue
            address = cand
            break
    if address is None:
        for cand in emails_in(text):
            if cand.startswith("mailer-daemon") or cand.startswith("postmaster"):
                continue
            address = cand
            break
    code_match = re.search(r"\b(55[0-4])\b", text)
    code = code_match.group(1) if code_match else None
    reason = _reason(text, code)
    return {
        "failed_address": address,
        "smtp_code": code,
        "reason": reason,
        "detail": clip(text, 180),
    }


def _reason(text: str, code: str | None) -> str:
    if re.search(r"domain not found|nxdomain|host not found|unrouteable|name service error", text, re.I):
        return "domain_not_found"
    if re.search(
        r"over quota|mailbox full|inbox full|quota exceeded|storage allocation|mailbox is full",
        text,
        re.I,
    ):
        return "over_quota"
    if re.search(
        r"no such user|user unknown|user not found|recipient not found|unknown user|"
        r"does not exist|no mailbox|mailbox unavailable",
        text,
        re.I,
    ):
        return "no_such_user"
    if code == "552":
        return "over_quota"
    if code == "550":
        return "no_such_user"
    if code in {"551", "553", "554"} or re.search(r"relay denied|rejected", text, re.I):
        return "rejected"
    return "unknown"


def looks_like_bounce(text: str, sender: str = "") -> bool:
    blob = f"{sender}\n{text}"
    low = blob.casefold()
    if any(token in low for token in ("mailer-daemon", "mail delivery subsystem", "postmaster@")):
        return True
    if any(
        token in low
        for token in (
            "undeliverable",
            "delivery status notification",
            "delivery failure",
            "delivery has failed",
        )
    ):
        return True
    if re.search(r"host not found|domain not found|nxdomain", blob, re.I) and emails_in(blob):
        return True
    if re.search(r"\b55[0-4]\b", blob) and re.search(
        r"recipient|failed|user unknown|no such user|mailbox|host not found",
        blob,
        re.I,
    ):
        return True
    return False
