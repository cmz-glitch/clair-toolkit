"""Closed-thread gate. Decides SAFE_TO_REPLY or BLOCK. Does not send."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from clair_toolkit.util import canon_label, from_us, load_json, now_dubai, our_set, parse_dt

_FINAL = frozenset({"FINALIZED", "DONE", "CLOSED"})


def _messages(payload) -> list[dict]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    if isinstance(payload.get("messages"), list):
        return [item for item in payload["messages"] if isinstance(item, dict)]
    if payload.get("from") or payload.get("subject") or payload.get("id"):
        return [payload]
    return []


def _labels(payload, messages: list[dict]) -> set[str]:
    labels: set[str] = set()
    if isinstance(payload, dict):
        for label in payload.get("labelIds") or []:
            labels.add(canon_label(label))
    for message in messages:
        for label in message.get("labelIds") or []:
            labels.add(canon_label(label))
    return labels


def _stamp(message: dict):
    return parse_dt(message.get("internalDate") or message.get("date"))


def check_thread(payload, ours, days: float = 7, now=None) -> dict:
    ours = our_set(ours)
    messages = _messages(payload)
    moment = now_dubai(now)
    labels = _labels(payload, messages)
    ordered = sorted(messages, key=lambda message: _stamp(message) or moment)
    last = ordered[-1] if ordered else None
    waiting = bool(last and from_us(last, ours))
    inbound = [message for message in ordered if not from_us(message, ours)]
    last_in = inbound[-1] if inbound else None

    finalized = False
    if isinstance(payload, dict) and (payload.get("finalized") or payload.get("closed")):
        finalized = True
    if any(label.upper() in _FINAL for label in labels):
        finalized = True
    archived = bool(labels) and "INBOX" not in labels

    reason = "open"
    verdict = "SAFE_TO_REPLY"
    if not messages:
        verdict, reason = "BLOCK", "empty"
    elif finalized:
        verdict, reason = "BLOCK", "finalized"
    elif archived:
        verdict, reason = "BLOCK", "archived"
    elif waiting:
        verdict, reason = "BLOCK", "already_replied"
    elif last_in is not None:
        stamp = _stamp(last_in)
        if stamp is not None:
            age = moment - stamp.astimezone(moment.tzinfo)
            if age > timedelta(days=days):
                verdict, reason = "BLOCK", "stale"

    return {"verdict": verdict, "reason": reason, "waiting_reply": waiting}


def check_path(path: Path, ours, days: float = 7, now=None) -> dict:
    return check_thread(load_json(path), ours, days=days, now=now)
