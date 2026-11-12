"""Milou question card builder + linter (Milou 12 Nov 2026, tested live).

Every card: allowCustom ON, multiSelect ON, 4-6 options, one question, first option primary,
no helpText / descriptions / steps, no letter prefixes, no "Other"/"Free text" option.
Prints the exact widget JSON to pass to SendToUser (type: widget). No dependencies.

  milou-card "Book the Şahin invoice?" "Yes, go ahead" "Yes, but…" "Not now" "No"
  python3 -m clair_toolkit.card --lint card.json
"""
from __future__ import annotations

import json
import re
import sys

MIN_OPT, MAX_OPT, MAX_LABEL = 4, 6, 60
BANNED = re.compile(r"^(other|free text|type (my|your) own|i'?ll type|something else\.?)$", re.I)
LETTER = re.compile(r"^\s*([A-F]|[1-6])[\).:\-]\s+")


class CardError(ValueError):
    pass


def problems(card: dict) -> list[str]:
    out = []
    w = card.get("widget", card)
    if card.get("type", "widget") != "widget":
        out.append("type must be widget")
    p = (w.get("prompt") or "").strip()
    if not p:
        out.append("prompt missing")
    elif "\n" in p:
        out.append("prompt must be one line")
    elif not p.endswith("?"):
        out.append("prompt must be one question ending with ?")
    elif p.count("?") > 1:
        out.append("one question only (several ? found)")
    if w.get("allowCustom") is not True:
        out.append("allowCustom must be true")
    if w.get("multiSelect") is not True:
        out.append("multiSelect must be true")
    for k in ("helpText", "steps", "dismissOnMoveOn"):
        if k in w:
            out.append(f"{k} not allowed")
    opts = w.get("options") or []
    if not MIN_OPT <= len(opts) <= MAX_OPT:
        out.append(f"need {MIN_OPT}-{MAX_OPT} options, got {len(opts)}")
    labels = []
    for i, o in enumerate(opts):
        lab = (o.get("label") or "").strip()
        if not lab:
            out.append(f"option {i+1} has no label")
            continue
        labels.append(lab.lower())
        if "\n" in lab or len(lab) > MAX_LABEL:
            out.append(f"option {i+1} must be one short line (≤{MAX_LABEL} chars)")
        if BANNED.match(lab):
            out.append(f"option {i+1} '{lab}' not allowed (the write-in box covers it)")
        if LETTER.match(lab):
            out.append(f"option {i+1} has a letter/number prefix (app adds A, B, C)")
        if "description" in o:
            out.append(f"option {i+1}: description not allowed")
        if o.get("style") == "primary" and i != 0:
            out.append("only the first (recommended) option may be primary")
    if len(set(labels)) != len(labels):
        out.append("duplicate option labels")
    if opts and opts[0].get("style") != "primary":
        out.append("first option must be the recommended one, style primary")
    return out


def build(prompt: str, labels: list[str], danger: list[int] | None = None) -> dict:
    opts = []
    for i, lab in enumerate(labels):
        o = {"label": lab.strip()}
        if i == 0:
            o["style"] = "primary"
        elif danger and i + 1 in danger:
            o["style"] = "danger"
        opts.append(o)
    card = {"type": "widget", "widget": {"prompt": prompt.strip(), "allowCustom": True,
                                         "multiSelect": True, "options": opts}}
    bad = problems(card)
    if bad:
        raise CardError("; ".join(bad))
    return card


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        if argv[:1] == ["--lint"]:
            src = argv[1] if len(argv) > 1 else "-"
            card = json.load(sys.stdin if src == "-" else open(src, encoding="utf-8"))
            bad = problems(card)
            print("OK" if not bad else "BROKEN CARD:\n- " + "\n- ".join(bad))
            return 0 if not bad else 2
        danger = []
        while argv and argv[0] == "--danger":
            danger.append(int(argv[1])); argv = argv[2:]
        if len(argv) < 2:
            print(__doc__); return 2
        print(json.dumps(build(argv[0], argv[1:], danger), ensure_ascii=False))
        return 0
    except CardError as e:
        print(f"BROKEN CARD: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
