"""Build a silent handoff for the owner bot. Never a note to the human owner."""

from __future__ import annotations

from pathlib import Path

from clair_toolkit.routing import route
from clair_toolkit.util import canon_label, clip, format_dubai, load_json

_SKIP_LABELS = frozenset(
    {
        "INBOX",
        "UNREAD",
        "SENT",
        "IMPORTANT",
        "STARRED",
        "CATEGORY_PERSONAL",
        "CATEGORY_UPDATES",
        "CATEGORY_PROMOTIONS",
        "CATEGORY_SOCIAL",
        "CATEGORY_FORUMS",
    }
)


def _text(data: dict) -> str:
    return "\n".join(
        str(data.get(key) or "")
        for key in ("subject", "snippet", "ask", "text", "body")
    )


def _labels(data: dict) -> str:
    labels = {canon_label(label) for label in (data.get("labels") or [])}
    for label in data.get("labels_remove") or []:
        labels.discard(canon_label(label))
    for label in data.get("labels_add") or []:
        labels.add(canon_label(label))
    shown = sorted(label for label in labels if label not in _SKIP_LABELS)
    return ", ".join(shown) if shown else "none"


def _ask(data: dict) -> str:
    bounce = data.get("bounce")
    if isinstance(bounce, dict) and (data.get("category") == "bounce" or bounce.get("failed_address")):
        code = bounce.get("smtp_code") or ""
        reason = bounce.get("reason") or "unknown"
        address = bounce.get("failed_address") or "unknown"
        bits = " ".join(bit for bit in (str(code), str(reason)) if bit)
        return clip(f"Bounce {bits} for {address}")
    if data.get("ask"):
        return clip(str(data["ask"]))
    subject = str(data.get("subject") or "").strip()
    snippet = str(data.get("snippet") or "").strip()
    return clip(subject or snippet)


def build_handoff(data: dict) -> dict:
    category = data.get("category") or "business"
    routed_owner, routed_rule = route(category, _text(data))
    owner = data.get("owner") or routed_owner
    rule = data.get("rule") or routed_rule
    if owner in {None, "", "UNKNOWN"} and routed_owner not in {None, "", "UNKNOWN"}:
        owner, rule = routed_owner, routed_rule
    if owner in {None, "UNKNOWN"}:
        return {"owner": "UNKNOWN", "rule": None, "ask_owner": True, "handoff": None}
    if owner in {"NONE", "Clair"} or not rule:
        return {
            "owner": owner if owner != "NONE" else "NONE",
            "rule": rule,
            "ask_owner": False,
            "handoff": None,
        }
    sent = "yes" if data.get("sent") else "no"
    lines = [
        f"Rule: {rule} (Clair routing; silent handoff t532u)",
        f"From: {data.get('from') or 'unknown'}",
        f"Date: {format_dubai(data.get('date') or data.get('date_dubai'))}",
        f"Thread: {data.get('thread_id') or 'unknown'}",
        f"Msg: {data.get('message_id') or 'unknown'}",
        f"Ask: {_ask(data)}",
        f"Labels: {_labels(data)}",
        f"Sent: {sent}",
    ]
    return {
        "owner": owner,
        "rule": rule,
        "ask_owner": False,
        "handoff": "\n".join(lines),
    }


def build_path(path: Path) -> dict:
    return build_handoff(load_json(path))
