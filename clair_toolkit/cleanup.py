"""Plan inbox cleanup. Prints a plan only; never deletes or moves mail."""

from __future__ import annotations

from pathlib import Path

from clair_toolkit.classify import classify_message, detect_category
from clair_toolkit.queue import parse_line
from clair_toolkit.util import (
    COLD,
    FATURA,
    NEED,
    WAITING,
    canon_label,
    from_us,
    load_json,
    our_set,
    parse_dt,
)


def _threads(payload) -> list[dict]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        return payload.get("threads") or []
    return []


def _labels(thread: dict) -> set[str]:
    labels = {canon_label(label) for label in (thread.get("labelIds") or [])}
    for message in thread.get("messages") or []:
        for label in message.get("labelIds") or []:
            labels.add(canon_label(label))
    return labels


def _thread_id(thread: dict) -> str:
    return str(thread.get("id") or thread.get("threadId") or "")


def _last_message(thread: dict) -> dict | None:
    messages = [message for message in (thread.get("messages") or []) if isinstance(message, dict)]
    if messages:
        def key(message):
            stamp = parse_dt(message.get("internalDate") or message.get("date"))
            return stamp.timestamp() if stamp else 0

        return max(messages, key=key)
    if any(thread.get(field) for field in ("last_from", "from", "subject", "snippet")):
        return {
            "id": thread.get("last_message_id") or thread.get("message_id"),
            "threadId": _thread_id(thread),
            "from": thread.get("last_from") or thread.get("from"),
            "date": thread.get("last_date") or thread.get("date"),
            "subject": thread.get("subject") or "",
            "snippet": thread.get("snippet") or "",
            "body": thread.get("body") or "",
            "labelIds": thread.get("labelIds") or [],
        }
    return None


def _handled(thread: dict, state: dict) -> bool:
    threads = state.get("handled_thread_ids") or {}
    messages = set(state.get("handled_message_ids") or [])
    if _thread_id(thread) in threads:
        return True
    ids = []
    if thread.get("last_message_id"):
        ids.append(str(thread["last_message_id"]))
    for message in thread.get("messages") or []:
        if message.get("id"):
            ids.append(str(message["id"]))
    return any(message_id in messages for message_id in ids)


def _open_blob(queue_paths: list[Path]) -> str:
    chunks = []
    for path in queue_paths:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            item = parse_line(line)
            if item and item["open"]:
                chunks.append(item["line"])
    return "\n".join(chunks).casefold()


def _queued(thread: dict, blob: str) -> bool:
    if not blob:
        return False
    candidates = [_thread_id(thread)]
    if thread.get("last_message_id"):
        candidates.append(str(thread["last_message_id"]))
    for message in thread.get("messages") or []:
        if message.get("id"):
            candidates.append(str(message["id"]))
    return any(len(item) >= 6 and item.casefold() in blob for item in candidates if item)


def _fixes(labels: set[str], last_ours: bool, action: str) -> dict | None:
    remove: list[str] = []
    reasons: list[str] = []
    if NEED in labels and last_ours:
        remove.append(NEED)
        reasons.append("reply_is_last")
    if COLD in labels and WAITING in labels:
        remove.append(WAITING)
        reasons.append("cold_not_waiting")
    elif WAITING in labels and not last_ours:
        remove.append(WAITING)
        reasons.append("they_replied")
    if action == "ARCHIVE" and NEED in labels and NEED not in remove:
        remove.append(NEED)
        reasons.append("drop_need_attention")
    if not remove:
        return None
    return {"remove": remove, "reason": "+".join(reasons)}


def _decide(labels: set[str], category: str | None, last_ours: bool, handled: bool, queued: bool) -> tuple[str, str]:
    if queued:
        return "KEEP", "open_queue"
    if FATURA in labels or category == "invoice":
        return "ARCHIVE", "invoice_filed"
    if category == "bounce":
        return "ARCHIVE", "bounce"
    if category == "auto-reply":
        return "ARCHIVE", "auto_reply"
    if category == "notification":
        return "ARCHIVE", "notification"
    if NEED in labels and not last_ours and not handled:
        return "KEEP", "need_attention_unanswered"
    if handled:
        return "ARCHIVE", "handled"
    if COLD in labels:
        return "ARCHIVE", "cold_mail"
    if WAITING in labels and last_ours:
        return "ARCHIVE", "waiting_reply"
    if last_ours:
        return "ARCHIVE", "answered"
    return "ARCHIVE", "not_kept"


def plan(payload, state: dict, ours, queue_paths: list[Path] | None = None) -> dict:
    ours = our_set(ours)
    blob = _open_blob(list(queue_paths or []))
    rows = []
    archive_ids = []
    fixes = []
    for thread in _threads(payload):
        labels = _labels(thread)
        last = _last_message(thread)
        last_ours = from_us(last, ours)
        category = detect_category(last, labels, ours) if last else None
        action, reason = _decide(labels, category, last_ours, _handled(thread, state), _queued(thread, blob))
        thread_id = _thread_id(thread)
        rows.append({"id": thread_id, "action": action, "reason": reason})
        if action == "ARCHIVE":
            archive_ids.append(thread_id)
        fix = _fixes(labels, last_ours, action)
        if fix:
            fixes.append({"id": thread_id, **fix})
    return {"plan": rows, "archive_ids": archive_ids, "label_fixes": fixes}


def plan_path(path: Path, state_path: Path, ours, queue_paths=None) -> dict:
    state = load_json(state_path) if state_path else {}
    return plan(load_json(path), state, ours, queue_paths)
