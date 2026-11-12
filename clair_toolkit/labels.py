"""Flag label combinations the triage rules forbid."""

from __future__ import annotations

from pathlib import Path

from clair_toolkit.util import COLD, FATURA, NEED, WAITING, canon_label, load_json


def _labels(thread: dict) -> set[str]:
    labels = {canon_label(label) for label in (thread.get("labelIds") or [])}
    for message in thread.get("messages") or []:
        for label in message.get("labelIds") or []:
            labels.add(canon_label(label))
    return labels


def _threads(payload) -> list[dict]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        return payload.get("threads") or payload.get("messages") or []
    return []


def check_labels(payload) -> dict:
    flags = []
    for thread in _threads(payload):
        labels = _labels(thread)
        if not labels:
            continue
        thread_id = thread.get("id") or thread.get("threadId")
        if COLD in labels and WAITING in labels:
            flags.append({"id": thread_id, "rule": "cold_and_waiting"})
        if NEED in labels and "INBOX" not in labels:
            flags.append({"id": thread_id, "rule": "need_attention_archived"})
        if FATURA in labels and "INBOX" in labels:
            flags.append({"id": thread_id, "rule": "invoice_not_archived"})
    return {"ok": True, "flags": flags}


def check_path(path: Path) -> dict:
    return check_labels(load_json(path))
