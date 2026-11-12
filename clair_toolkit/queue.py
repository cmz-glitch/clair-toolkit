"""Append, close, list, and chase lines in a bot queue markdown file."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from clair_toolkit.util import DUBAI, atomic_write, now_dubai

_SPLIT = re.compile(r"\s+[|·]\s+")
_ITEM = re.compile(r"^- \[(?P<box>[ xX])\]\s+(?P<rest>.*)$")


def parse_line(line: str) -> dict | None:
    match = _ITEM.match(line.rstrip("\n"))
    if not match:
        return None
    parts = [part.strip() for part in _SPLIT.split(match.group("rest"))]
    if len(parts) < 4:
        return None
    when, sender, ref = parts[0], parts[1], parts[-1]
    task = " | ".join(parts[2:-1])
    return {
        "open": match.group("box") == " ",
        "at": when,
        "from": sender,
        "task": task,
        "ref": ref,
        "line": line.rstrip("\n"),
    }


def _when(item: dict) -> datetime | None:
    text = item["at"]
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=DUBAI)
        except ValueError:
            continue
    return None


def _read(path: Path) -> list[str]:
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8").splitlines()


def _write(path: Path, lines: list[str]) -> None:
    text = "\n".join(lines)
    if not text.endswith("\n"):
        text += "\n"
    atomic_write(path, text)


def _ref_hit(item: dict, ref: str) -> bool:
    needle = ref.strip().casefold()
    if len(needle) < 4:
        return False
    return needle in item["ref"].casefold()


def public_item(item: dict) -> dict:
    return {
        "at": item["at"],
        "from": item["from"],
        "task": item["task"],
        "ref": item["ref"],
        "line": item["line"],
    }


def append_item(path: Path, sender: str, task: str, ref: str, at: str | None = None) -> dict:
    lines = _read(path)
    for line in lines:
        item = parse_line(line)
        if item and item["open"] and _ref_hit(item, ref):
            return {"appended": False, "line": item["line"]}
    stamp = at or now_dubai().strftime("%Y-%m-%d %H:%M")
    new = f"- [ ] {stamp} | {sender} | {task} | {ref}"
    if lines and lines[-1] == "":
        lines[-1] = new
    else:
        lines.append(new)
    _write(path, lines)
    return {"appended": True, "line": new}


def mark_done(path: Path, ref: str) -> dict:
    lines = _read(path)
    updated = 0
    already = 0
    matched = False
    for index, line in enumerate(lines):
        item = parse_line(line)
        if not item or not _ref_hit(item, ref):
            continue
        matched = True
        if item["open"]:
            lines[index] = re.sub(r"^- \[ \]", "- [x]", line, count=1)
            updated += 1
        else:
            already += 1
    if matched and updated:
        _write(path, lines)
    return {"updated": updated, "already_done": already}


def list_open(path: Path) -> dict:
    items = []
    for line in _read(path):
        item = parse_line(line)
        if item and item["open"]:
            items.append(public_item(item))
    return {"open": items}


def chase(path: Path, hours: float, bot: str | None = None, now: str | None = None) -> dict:
    moment = now_dubai(now)
    found = []
    for line in _read(path):
        item = parse_line(line)
        if not item or not item["open"]:
            continue
        if bot and bot.casefold() not in item["from"].casefold():
            continue
        stamp = _when(item)
        if stamp is None:
            continue
        age = (moment - stamp).total_seconds() / 3600
        if age > hours:
            row = public_item(item)
            row["age_hours"] = round(age, 2)
            found.append(row)
    payload = {"chase": found, "hours": hours}
    if bot:
        payload["bot"] = bot
    return payload
