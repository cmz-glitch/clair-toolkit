"""Shared file, date, email, and money helpers. Stdlib only."""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from email.utils import parsedate_to_datetime
from pathlib import Path
from zoneinfo import ZoneInfo

DUBAI = ZoneInfo("Asia/Dubai")

EMAIL_RE = re.compile(r"[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}", re.I)

FREEMAIL = frozenset(
    {
        "gmail.com",
        "googlemail.com",
        "hotmail.com",
        "hotmail.com.tr",
        "outlook.com",
        "yahoo.com",
        "yahoo.com.tr",
        "icloud.com",
        "live.com",
        "yandex.com",
        "yandex.ru",
        "msn.com",
        "aol.com",
        "proton.me",
        "protonmail.com",
    }
)

FATURA = "Label_1"
NEED = "Label_4"
WAITING = "Label_9"
COLD = "Label_12"
ONGOING = "Label_13"
SAMPLE = "Label_14"

_LABEL_ALIAS = {
    "fatura irsaliye": FATURA,
    "need attention": NEED,
    "waiting reply": WAITING,
    "cold mails": COLD,
    "ongoing prospection": ONGOING,
    "sample sent": SAMPLE,
    "inbox": "INBOX",
}


def emit(obj: object) -> None:
    sys.stdout.write(json.dumps(obj, ensure_ascii=False, separators=(",", ":")))
    sys.stdout.write("\n")


def load_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def atomic_write(path: Path, text: str) -> None:
    path = Path(path)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def decode_bytes(raw: bytes) -> str:
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16")
    for enc in ("utf-8-sig", "utf-8", "cp1254"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1")


def emails_in(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        out: list[str] = []
        for item in value:
            out.extend(emails_in(item))
        return out
    return [m.casefold() for m in EMAIL_RE.findall(str(value))]


def domain_of(email: str) -> str:
    email = email.strip().casefold()
    if "@" not in email:
        return ""
    return email.rsplit("@", 1)[1]


def is_freemail(domain: str) -> bool:
    return domain.casefold() in FREEMAIL


def canon_label(label: str) -> str:
    text = str(label).strip()
    return _LABEL_ALIAS.get(text.casefold(), text)


def parse_dt(value) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, (int, float)):
        n = float(value)
        if n > 10_000_000_000:
            n /= 1000.0
        return datetime.fromtimestamp(n, tz=timezone.utc)
    text = str(value).strip()
    if re.fullmatch(r"\d{10,13}", text):
        n = float(text)
        if n > 10_000_000_000:
            n /= 1000.0
        return datetime.fromtimestamp(n, tz=timezone.utc)
    wall = re.fullmatch(r"(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2})(?::\d{2})?", text)
    if wall:
        return datetime.strptime(
            wall.group(1) + " " + wall.group(2), "%Y-%m-%d %H:%M"
        ).replace(tzinfo=DUBAI)
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        dt = None
    if dt is not None:
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    try:
        dt = parsedate_to_datetime(text)
    except (TypeError, ValueError, IndexError, OverflowError):
        return None
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def as_dubai(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=DUBAI)
    return dt.astimezone(DUBAI)


def format_dubai(value) -> str:
    if isinstance(value, str) and value.strip().endswith(" Dubai"):
        value = value.strip()[: -len(" Dubai")].strip()
    dt = parse_dt(value)
    if dt is None:
        return "unknown"
    return as_dubai(dt).strftime("%Y-%m-%d %H:%M") + " Dubai"


def now_dubai(value=None) -> datetime:
    if value:
        dt = parse_dt(value)
        if dt is None:
            raise ValueError(f"bad time: {value}")
        return as_dubai(dt)
    return datetime.now(DUBAI)


def parse_tr_amount(raw) -> Decimal | None:
    if raw is None:
        return None
    text = str(raw).strip()
    text = re.sub(r"(?i)\b(tl|try|usd|eur)\b", "", text)
    text = text.replace("€", "").replace("$", "")
    text = re.sub(r"\s+", "", text)
    if not re.search(r"\d", text):
        return None
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    elif "," in text:
        text = text.replace(",", ".")
    try:
        return Decimal(text).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except Exception:
        return None


def format_tr_amount(amount: Decimal) -> str:
    quant = Decimal(amount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    sign = "-" if quant < 0 else ""
    quant = abs(quant)
    whole, frac = f"{quant:.2f}".split(".")
    groups: list[str] = []
    while whole:
        groups.append(whole[-3:])
        whole = whole[:-3]
    return sign + ".".join(reversed(groups)) + "," + frac


def money_str(amount: Decimal | None) -> str | None:
    if amount is None:
        return None
    quant = Decimal(amount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{quant:.2f}"


def clip(text: str, limit: int = 180) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def our_set(values) -> set[str]:
    out: set[str] = set()
    for value in values or []:
        for part in str(value).split(","):
            out.update(emails_in(part))
            part = part.strip().casefold()
            if "@" in part and part not in out:
                out.add(part)
    return out


def from_us(message: dict | None, ours: set[str]) -> bool:
    if not message or not ours:
        return False
    return bool(set(emails_in(message.get("from"))) & ours)
