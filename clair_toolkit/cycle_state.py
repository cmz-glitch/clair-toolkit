"""Idempotent updates for cycle_state.json. Other keys stay put."""

from __future__ import annotations

import json
from pathlib import Path

from clair_toolkit.util import atomic_write, load_json


def _load(path: Path) -> dict:
    if not path.exists():
        return {}
    data = load_json(path)
    if not isinstance(data, dict):
        raise ValueError("cycle_state must be a JSON object")
    return data


def _save(path: Path, data: dict) -> None:
    atomic_write(path, json.dumps(data, ensure_ascii=False, indent=1) + "\n")


def _threads(data: dict) -> dict:
    threads = data.get("handled_thread_ids")
    if not isinstance(threads, dict):
        threads = {}
        data["handled_thread_ids"] = threads
    return threads


def _messages(data: dict) -> list:
    messages = data.get("handled_message_ids")
    if not isinstance(messages, list):
        messages = []
        data["handled_message_ids"] = messages
    return messages


def _followups(data: dict) -> list:
    rows = data.get("no_followup")
    if not isinstance(rows, list):
        rows = []
        data["no_followup"] = rows
    return rows


def is_handled(path: Path, thread: str, message: str | None = None) -> dict:
    data = _load(path)
    threads = data.get("handled_thread_ids") or {}
    messages = data.get("handled_message_ids") or []
    followups = data.get("no_followup") or []
    via = None
    if thread in threads:
        via = "thread"
    elif message and message in messages:
        via = "message"
    no_follow = any(
        isinstance(row, dict)
        and (row.get("thread_id") == thread or (message and row.get("thread_id") == message))
        for row in followups
    )
    payload = {"handled": via is not None, "no_followup": no_follow}
    if via:
        payload["via"] = via
    return payload


def mark_handled(path: Path, thread: str, note: str, message: str | None = None) -> dict:
    data = _load(path)
    threads = _threads(data)
    changed = False
    if thread not in threads:
        threads[thread] = note
        changed = True
    if message:
        messages = _messages(data)
        if message not in messages:
            messages.append(message)
            changed = True
    if changed:
        _save(path, data)
    return {"handled": True, "changed": changed}


def add_no_followup(
    path: Path,
    company: str,
    email: str,
    domain: str,
    thread: str,
    reason: str,
    date: str,
    confirmed: str | None = None,
) -> dict:
    data = _load(path)
    rows = _followups(data)
    email_key = email.casefold()
    for row in rows:
        if not isinstance(row, dict):
            continue
        same_thread = row.get("thread_id") == thread
        same_email = str(row.get("email") or "").casefold() == email_key
        if same_thread or same_email:
            return {"added": False, "reason": "exists"}
    entry = {
        "company": company,
        "email": email,
        "domain": domain,
        "thread_id": thread,
        "reason": reason,
        "date": date,
    }
    if confirmed:
        entry["confirmed"] = confirmed
    rows.append(entry)
    _save(path, data)
    return {"added": True}
