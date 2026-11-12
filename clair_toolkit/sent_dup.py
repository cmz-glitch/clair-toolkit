"""Flag earlier Sent-mail to the same address or company domain."""

from __future__ import annotations

import re
from pathlib import Path

from clair_toolkit.util import domain_of, emails_in, is_freemail, load_json

_REPLY = re.compile(r"^(?:re|fw|fwd)\s*:\s*", re.I)


def _messages(payload) -> list[dict]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        return payload.get("messages") or payload.get("sent") or []
    return []


def _norm_subject(text: str) -> str:
    text = text or ""
    while True:
        nxt = _REPLY.sub("", text.strip())
        if nxt == text.strip():
            break
        text = nxt
    return re.sub(r"\s+", " ", text).strip().casefold()


def _subject_hit(candidate: str, sent: str) -> bool:
    left, right = _norm_subject(candidate), _norm_subject(sent)
    if not left or not right:
        return False
    return left in right or right in left


def _keywords_hit(keywords: list[str], message: dict) -> bool:
    if not keywords:
        return True
    blob = " ".join(
        [
            str(message.get("subject") or ""),
            str(message.get("snippet") or ""),
            str(message.get("body") or ""),
        ]
    ).casefold()
    return all(word.casefold() in blob for word in keywords)


def find_duplicates(payload, recipients: list[str], subject: str | None, keywords: list[str]) -> dict:
    messages = _messages(payload)
    matches = []
    seen = set()
    for recipient in recipients:
        email = (emails_in(recipient) or [recipient.strip().casefold()])[0]
        domain = domain_of(email)
        for message in messages:
            sent_to = set(emails_in(message.get("to")) + emails_in(message.get("cc")))
            via = None
            if email in sent_to:
                via = "address"
            elif domain and not is_freemail(domain):
                if any(domain_of(addr) == domain for addr in sent_to):
                    via = "domain"
            if not via:
                continue
            if subject and not _subject_hit(subject, str(message.get("subject") or "")):
                continue
            if not _keywords_hit(keywords, message):
                continue
            key = (email, message.get("id"), via)
            if key in seen:
                continue
            seen.add(key)
            matches.append(
                {
                    "email": email,
                    "via": via,
                    "id": message.get("id"),
                    "date": message.get("date"),
                    "subject": message.get("subject"),
                }
            )
    return {"hit": bool(matches), "matches": matches}


def find_path(path: Path, recipients, subject, keywords) -> dict:
    return find_duplicates(load_json(path), recipients, subject, keywords)
