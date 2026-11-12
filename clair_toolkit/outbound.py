"""Lint a draft email or WhatsApp against the short-mail and outbound rules."""

from __future__ import annotations

import re
from pathlib import Path

from clair_toolkit.language import detect_lang
from clair_toolkit.util import EMAIL_RE

_ALLOWED = re.compile(r"^(hello|hi|merhaba)\b", re.I)
_PURE = re.compile(r"^(hello|hi|merhaba)\b[\s,!.]*$", re.I)
_FORBIDDEN = re.compile(
    r"^(good\s+morning|good\s+afternoon|good\s+evening|g[uü]nayd[ıi]n|bonjour|bonsoir|dear|say[ıi]n|selam)\b",
    re.I,
)
_SIGN_OFF = re.compile(
    r"^(regards|best regards|kind regards|sayg[ıi]lar[ıi]mla|iyi [cç]al[ıi][sş]malar|sent from)\b",
    re.I,
)
_PS = re.compile(r"(?i)(?:^|[\s(])p\.?\s?s\.?(?:[\s:.\-]|$)")
_PO = re.compile(r"\b(?:PO|CO|PROV)\d{2,}(?:-\d+)?\b")
_PHONE = re.compile(r"\+?\d[\d\s().-]{8,}\d")

_DEFAULT = Path(__file__).resolve().parent / "data" / "deny_list.txt"


def _has_phone(text: str) -> bool:
    for match in _PHONE.finditer(text or ""):
        digits = re.sub(r"\D", "", match.group())
        if 10 <= len(digits) <= 15:
            return True
    return False


def _split_signature(text: str) -> tuple[str, str]:
    lines = text.splitlines()
    last_blank = None
    for index, line in enumerate(lines):
        if not line.strip():
            last_blank = index
    if last_blank is None:
        return text, ""
    tail = "\n".join(lines[last_blank + 1 :]).strip()
    if not tail:
        return text, ""
    if _has_phone(tail) or EMAIL_RE.search(tail) or _SIGN_OFF.search(tail):
        return "\n".join(lines[:last_blank]), tail
    return text, ""


def _first_line(text: str) -> str:
    for line in text.splitlines():
        if line.strip():
            return line.strip()
    return ""


def sentence_count(text: str) -> int:
    body, _sig = _split_signature(text)
    count = 0
    buf: list[str] = []
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if _has_phone(stripped) and len(stripped) < 40:
            continue
        if _PURE.match(stripped):
            count += 1
            continue
        buf.append(stripped)
    blob = " ".join(buf)
    parts = [part for part in re.split(r"[.!?]+", blob) if part.strip()]
    return count + len(parts)


def _load_terms(deny_file: Path | None, extra: list[str]) -> list[tuple[str, str]]:
    terms: list[tuple[str, str]] = []
    path = deny_file if deny_file is not None else _DEFAULT
    if path and Path(path).exists():
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            terms.append(_parse_term(line))
    for item in extra:
        terms.append(_parse_term(item))
    return terms


def _parse_term(line: str) -> tuple[str, str]:
    parts = line.split(None, 1)
    if len(parts) == 2 and parts[0] in {"B", "C"}:
        return parts[0], parts[1].strip()
    return "B", line.strip()


def _denied(text: str, terms: list[tuple[str, str]]) -> list[str]:
    reasons = []
    for klass, term in terms:
        if not term:
            continue
        pattern = r"(?<!\w)" + re.escape(term.casefold()) + r"(?!\w)"
        if re.search(pattern, text.casefold()):
            label = "C" if klass == "C" else "B"
            reasons.append(f"{label}: denied term {term}")
    return reasons


def _greeting_reasons(text: str, channel: str, thread_lang: str | None, first_of_day: bool) -> list[str]:
    first = _first_line(text)
    if not first:
        return ["G: greeting must be Hello, Hi, or Merhaba"]
    if _FORBIDDEN.match(first):
        return ["G: greeting must be Hello, Hi, or Merhaba"]
    if channel == "email":
        if not _ALLOWED.match(first):
            return ["G: greeting must be Hello, Hi, or Merhaba"]
        return []
    if first_of_day:
        if (thread_lang or "").upper() == "TR":
            if not re.match(r"^merhaba\b", first, re.I):
                return ["G: TR first message must open with Merhaba"]
        elif not _ALLOWED.match(first):
            return ["G: first message must open with Hello, Hi, or Merhaba"]
    return []


def _language_reasons(text: str, thread_lang: str | None) -> list[str]:
    if not thread_lang:
        return ["F: thread language missing"]
    body, _sig = _split_signature(text)
    kept = []
    for line in body.splitlines():
        if _PURE.match(line.strip()):
            continue
        kept.append(line)
    detected = detect_lang("\n".join(kept))
    wanted = thread_lang.upper()
    if detected == "unknown":
        return ["F: could not read draft language"]
    if detected != wanted:
        return [f"F: draft is {detected}, thread is {wanted}"]
    return []


def lint(
    text: str,
    channel: str,
    thread_lang: str | None = None,
    follow_up: bool = False,
    first_of_day: bool = False,
    deny: list[str] | None = None,
    deny_file: Path | None = None,
) -> dict:
    channel = channel.casefold()
    reasons: list[str] = []
    reasons.extend(_greeting_reasons(text, channel, thread_lang, first_of_day))
    _body, signature = _split_signature(text)
    if channel == "whatsapp":
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        last = lines[-1] if lines else ""
        trailing = bool(signature.strip()) or bool(_SIGN_OFF.match(last)) or (
            bool(last) and _has_phone(last) and len(last) < 40
        ) or bool(EMAIL_RE.search(last) and len(last) < 60)
        if trailing:
            reasons.append("I: WhatsApp has no signature")
    else:
        if not signature.strip() or not _has_phone(signature):
            reasons.append("I: email signature must include the phone number")
    reasons.extend(_language_reasons(text, thread_lang))
    if _PS.search(text):
        reasons.append("PS: no postscript")
    count = sentence_count(text)
    if follow_up and count != 2:
        reasons.append(f"LEN: follow-up is 2 sentences, got {count}")
    elif not follow_up and not 3 <= count <= 5:
        reasons.append(f"LEN: 3 to 5 sentences, got {count}")
    reasons.extend(_denied(text, _load_terms(deny_file, deny or [])))
    if _PO.search(text):
        reasons.append("B: do not detail a PO or CO in the body")
    verdict = "PASS" if not reasons else "FAIL"
    return {"verdict": verdict, "reasons": reasons}
