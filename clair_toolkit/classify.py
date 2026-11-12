"""Label one message with a rule category, owner, and label changes."""

from __future__ import annotations

import re
from pathlib import Path

from clair_toolkit.bounce import looks_like_bounce, parse_bounce
from clair_toolkit.routing import route
from clair_toolkit.util import (
    COLD,
    FATURA,
    NEED,
    ONGOING,
    WAITING,
    canon_label,
    clip,
    emails_in,
    format_dubai,
    from_us,
    load_json,
    our_set,
)

_AUTO = re.compile(
    r"out of office|automatic reply|auto-reply|autoreply|auto reply|"
    r"otomatik yan[ıi]t|otomatik cevap|"
    r"i am currently out|i'm currently out|away from the office|"
    r"tatildeyim|y[ıi]ll[ıi]k izin|"
    r"auto-submitted:\s*auto-replied",
    re.I,
)
_HR = re.compile(
    r"\bsgk\b|\bssk\b|bordro|maa[sş]|salary|payroll|[oö]zl[uü]k|"
    r"insan kaynaklar[ıi]|i[sş]e giri[sş]|i[sş]ten [cç][ıi]k[ıi][sş]|\bpersonel\b",
    re.I,
)
_INVOICE_NO = re.compile(r"\b[A-Z][A-Z0-9]{2}\d{13}\b")
_INVOICE_WORD = re.compile(
    r"e-?\s?fatura|e-?\s?ar[sş]iv|\birsaliye\b|\bfatura\b|invoice no|fatura no",
    re.I,
)


def message_blob(message: dict) -> str:
    headers = message.get("headers") or {}
    header_bits = ""
    if isinstance(headers, dict):
        header_bits = " ".join(f"{key}: {value}" for key, value in headers.items())
    return "\n".join(
        [
            str(message.get("subject") or ""),
            str(message.get("snippet") or ""),
            str(message.get("body") or ""),
            header_bits,
        ]
    )


def _labels(message: dict, thread_labels) -> set[str]:
    labels = {canon_label(label) for label in (thread_labels or [])}
    for label in message.get("labelIds") or []:
        labels.add(canon_label(label))
    return labels


def _sender_local(message: dict) -> str:
    found = emails_in(message.get("from"))
    if not found:
        return ""
    return found[0].split("@", 1)[0]


def _is_notification(message: dict, text: str) -> bool:
    if _INVOICE_WORD.search(text) or _INVOICE_NO.search(text):
        return False
    local = _sender_local(message)
    if any(token in local for token in ("noreply", "no-reply", "donotreply", "notifications", "newsletter")):
        return True
    low = text.casefold()
    if "unsubscribe" in low or "newsletter" in low:
        return True
    headers = message.get("headers") or {}
    if isinstance(headers, dict):
        if headers.get("List-Unsubscribe"):
            return True
        if str(headers.get("Precedence") or "").casefold() == "bulk":
            return True
    return False


def _is_auto(message: dict, text: str) -> bool:
    headers = message.get("headers") or {}
    if isinstance(headers, dict) and str(headers.get("Auto-Submitted") or "").casefold().startswith("auto"):
        return True
    return bool(_AUTO.search(text))


def _is_invoice(text: str, labels: set[str]) -> bool:
    if FATURA in labels:
        return True
    return bool(_INVOICE_NO.search(text) or _INVOICE_WORD.search(text))


def detect_category(message: dict, thread_labels=None, ours=None) -> str:
    ours = our_set(ours)
    text = message_blob(message)
    labels = _labels(message, thread_labels)
    sender = str(message.get("from") or "")
    if looks_like_bounce(text, sender):
        return "bounce"
    if _is_auto(message, text):
        return "auto-reply"
    if _is_invoice(text, labels):
        return "invoice"
    if _HR.search(text):
        return "HR-SGK"
    if COLD in labels and not from_us(message, ours):
        return "cold-reply"
    if _is_notification(message, text):
        return "notification"
    return "business"


def _label_plan(category: str, owner: str, labels: set[str], sent: bool) -> tuple[list[str], list[str], bool, str]:
    add: list[str] = []
    remove: list[str] = []
    archive = False
    action = "handoff"
    if category == "invoice":
        add.append(FATURA)
        remove.extend([NEED, WAITING])
        archive = True
        action = "archive"
    elif category in {"bounce", "auto-reply", "notification"}:
        remove.extend([NEED, WAITING])
        archive = True
        action = "archive"
    elif category == "cold-reply":
        add.append(ONGOING)
        remove.extend([COLD, WAITING])
        action = "handoff"
    elif category == "HR-SGK":
        action = "handoff"
    elif owner == "Catalina":
        remove.append(WAITING)
        action = "handoff"
    elif owner in {"Vega", "Christina"}:
        action = "handoff"
    elif category == "business" and not sent and WAITING in labels and owner == "Clair":
        remove.append(WAITING)
        action = "thank_you"
    elif not sent and owner in {"Clair", "UNKNOWN"}:
        add.append(NEED)
        action = "check_sent" if owner == "Clair" else "ask_owner"
    elif sent:
        remove.append(NEED)
        action = "none"
    if archive:
        remove.append("INBOX")
    # Stable, unique, and don't add a label we also remove.
    remove = [label for label in dict.fromkeys(remove) if label not in add or label == "INBOX"]
    add = [label for label in dict.fromkeys(add) if label not in remove]
    return add, remove, archive, action


def classify_message(message: dict, thread_labels=None, ours=None) -> dict:
    ours = our_set(ours)
    text = message_blob(message)
    labels = _labels(message, thread_labels)
    category = detect_category(message, thread_labels, ours)
    sent = from_us(message, ours)
    owner, rule = route(category, text)
    # A plain business reply on a thread we were waiting on is Clair's thank-you,
    # unless a specialist owner already claimed it.
    if (
        category == "business"
        and owner == "UNKNOWN"
        and not sent
        and WAITING in labels
        and not re.search(r"not interested|ilgilenmiyoruz", text, re.I)
    ):
        owner = "Clair"
        rule = "answer to our question -> Clair thank-you"
    add, remove, archive, action = _label_plan(category, owner, labels, sent)
    if action == "thank_you" and owner == "UNKNOWN":
        owner = "Clair"
    bounce = parse_bounce(text) if category == "bounce" else None
    ask = _ask(category, message, bounce)
    return {
        "category": category,
        "owner": owner,
        "rule": rule,
        "labels_add": add,
        "labels_remove": remove,
        "archive": archive,
        "action": action,
        "from": message.get("from"),
        "date": message.get("date") or message.get("internalDate"),
        "date_dubai": format_dubai(message.get("date") or message.get("internalDate")),
        "subject": message.get("subject") or "",
        "snippet": clip(str(message.get("snippet") or ""), 160),
        "ask": ask,
        "thread_id": message.get("threadId") or message.get("thread_id"),
        "message_id": message.get("id") or message.get("message_id"),
        "labels": sorted(labels),
        "sent": sent,
        "text": clip(text, 500),
        "bounce": bounce,
    }


def _ask(category: str, message: dict, bounce) -> str:
    if category == "bounce" and bounce:
        code = bounce.get("smtp_code") or ""
        reason = bounce.get("reason") or "unknown"
        address = bounce.get("failed_address") or "unknown"
        bits = " ".join(bit for bit in (code, reason) if bit)
        return clip(f"Bounce {bits} for {address}")
    subject = re.sub(r"^(?:re|fw|fwd)\s*:\s*", "", str(message.get("subject") or ""), flags=re.I).strip()
    snippet = str(message.get("snippet") or "").strip()
    if subject and snippet and snippet.casefold() not in subject.casefold():
        return clip(f"{subject} — {snippet}")
    return clip(subject or snippet or str(message.get("body") or ""))


def classify_payload(payload, ours=None) -> dict:
    if isinstance(payload, dict) and isinstance(payload.get("messages"), list) and payload["messages"]:
        labels = list(payload.get("labelIds") or [])
        for message in payload["messages"]:
            labels.extend(message.get("labelIds") or [])
        last = payload["messages"][-1]
        if last.get("threadId") is None and payload.get("id"):
            last = dict(last)
            last["threadId"] = payload.get("id")
        return classify_message(last, labels, ours)
    if isinstance(payload, dict):
        return classify_message(payload, payload.get("labelIds"), ours)
    raise ValueError("message JSON object required")


def classify_path(path: Path, ours=None) -> dict:
    return classify_payload(load_json(path), ours)
