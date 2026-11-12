"""One entry point: python -m clair_toolkit <tool> ..."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from clair_toolkit.util import emit


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="clair_toolkit")
    sub = parser.add_subparsers(dest="tool", required=True)

    ef = sub.add_parser("efatura", help="parse a Turkish e-fatura HTML or PDF")
    ef.add_argument("path")
    ef.add_argument("--thread")
    ef.add_argument("--at", help="queue timestamp YYYY-MM-DD HH:MM")

    queue = sub.add_parser("queue", help="append, close, list, or chase a queue file")
    qsub = queue.add_subparsers(dest="action", required=True)
    add = qsub.add_parser("append")
    add.add_argument("path")
    add.add_argument("--from", dest="sender", required=True)
    add.add_argument("--task", required=True)
    add.add_argument("--ref", required=True)
    add.add_argument("--at")
    done = qsub.add_parser("done")
    done.add_argument("path")
    done.add_argument("--ref", required=True)
    listing = qsub.add_parser("list")
    listing.add_argument("path")
    chase = qsub.add_parser("chase")
    chase.add_argument("path")
    chase.add_argument("--hours", type=float, required=True)
    chase.add_argument("--bot")
    chase.add_argument("--now")

    cycle = sub.add_parser("cycle", help="handled ids and no-followup on cycle_state.json")
    csub = cycle.add_subparsers(dest="action", required=True)
    seen = csub.add_parser("is-handled")
    seen.add_argument("path")
    seen.add_argument("--thread", required=True)
    seen.add_argument("--message")
    mark = csub.add_parser("mark-handled")
    mark.add_argument("path")
    mark.add_argument("--thread", required=True)
    mark.add_argument("--note", required=True)
    mark.add_argument("--message")
    stop = csub.add_parser("add-no-followup")
    stop.add_argument("path")
    stop.add_argument("--company", required=True)
    stop.add_argument("--email", required=True)
    stop.add_argument("--domain", required=True)
    stop.add_argument("--thread", required=True)
    stop.add_argument("--reason", required=True)
    stop.add_argument("--date", required=True)
    stop.add_argument("--confirmed")

    gate = sub.add_parser("gate", help="SAFE_TO_REPLY or BLOCK")
    gate.add_argument("path")
    gate.add_argument("--ours", action="append", required=True)
    gate.add_argument("--days", type=float, default=7)
    gate.add_argument("--now")

    sent = sub.add_parser("sent-dup", help="earlier sends to the same address or domain")
    sent.add_argument("path")
    sent.add_argument("--to", action="append", required=True)
    sent.add_argument("--subject")
    sent.add_argument("--keyword", action="append")

    classify = sub.add_parser("classify", help="rule label for one message")
    classify.add_argument("path")
    classify.add_argument("--ours", action="append")

    bounce = sub.add_parser("bounce", help="failed address and reason")
    bounce.add_argument("path")

    lang = sub.add_parser("lang", help="TR EN FR AR ZH")
    lang.add_argument("path", nargs="?")
    lang.add_argument("--text")

    lint = sub.add_parser("lint", help="outbound draft check")
    lint.add_argument("--channel", required=True, choices=["email", "whatsapp"])
    lint.add_argument("--text")
    lint.add_argument("--text-file")
    lint.add_argument("--thread-lang")
    lint.add_argument("--follow-up", action="store_true")
    lint.add_argument("--first-of-day", action="store_true")
    lint.add_argument("--deny", action="append")
    lint.add_argument("--deny-file")

    dedupe = sub.add_parser("dedupe", help="cold contacts already emailed")
    dedupe.add_argument("path")
    dedupe.add_argument("--email", action="append", required=True)

    labels = sub.add_parser("labels", help="label combination check")
    labels.add_argument("path")

    cleanup = sub.add_parser("cleanup", help="KEEP or ARCHIVE plan; changes nothing")
    cleanup.add_argument("path")
    cleanup.add_argument("--state", required=True)
    cleanup.add_argument("--ours", action="append", required=True)
    cleanup.add_argument("--queue", action="append")

    handoff = sub.add_parser("handoff", help="silent handoff text for the owner bot")
    handoff.add_argument("path")
    return parser


def main(argv=None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        return _run(args)
    except FileNotFoundError as exc:
        emit({"ok": False, "error": "not_found", "path": str(exc.filename or exc)})
        return 1


def _run(args) -> int:
    tool = args.tool
    if tool == "efatura":
        from clair_toolkit.efatura import EdmShell, NoInvoiceText, parse_invoice

        try:
            payload = parse_invoice(Path(args.path), thread=args.thread, at=args.at)
        except EdmShell:
            emit({"ok": False, "error": "edm_shell"})
            return 1
        except NoInvoiceText as exc:
            emit({"ok": False, "error": str(exc)})
            return 1
        emit(payload)
        return 0 if payload.get("invoice_no") else 1
    if tool == "queue":
        from clair_toolkit import queue as queue_mod

        path = Path(args.path)
        if args.action == "append":
            emit(queue_mod.append_item(path, args.sender, args.task, args.ref, args.at))
        elif args.action == "done":
            emit(queue_mod.mark_done(path, args.ref))
        elif args.action == "list":
            emit(queue_mod.list_open(path))
        else:
            emit(queue_mod.chase(path, args.hours, args.bot, args.now))
        return 0
    if tool == "cycle":
        from clair_toolkit import cycle_state as cycle

        path = Path(args.path)
        if args.action == "is-handled":
            emit(cycle.is_handled(path, args.thread, args.message))
        elif args.action == "mark-handled":
            emit(cycle.mark_handled(path, args.thread, args.note, args.message))
        else:
            emit(
                cycle.add_no_followup(
                    path,
                    args.company,
                    args.email,
                    args.domain,
                    args.thread,
                    args.reason,
                    args.date,
                    args.confirmed,
                )
            )
        return 0
    if tool == "gate":
        from clair_toolkit.gate import check_path

        emit(check_path(Path(args.path), args.ours, days=args.days, now=args.now))
        return 0
    if tool == "sent-dup":
        from clair_toolkit.sent_dup import find_path

        emit(find_path(Path(args.path), args.to, args.subject, args.keyword or []))
        return 0
    if tool == "classify":
        from clair_toolkit.classify import classify_path

        emit(classify_path(Path(args.path), args.ours))
        return 0
    if tool == "bounce":
        from clair_toolkit.bounce import parse_bounce
        from clair_toolkit.util import load_json

        path = Path(args.path)
        raw = path.read_text(encoding="utf-8")
        if raw.lstrip().startswith("{") or raw.lstrip().startswith("["):
            data = load_json(path)
            if isinstance(data, dict):
                raw = "\n".join(
                    str(data.get(key) or "") for key in ("from", "subject", "snippet", "body")
                )
        emit(parse_bounce(raw))
        return 0
    if tool == "lang":
        from clair_toolkit.language import detect_lang

        if args.text is not None:
            text = args.text
        elif args.path:
            text = Path(args.path).read_text(encoding="utf-8")
        else:
            emit({"ok": False, "error": "missing_text"})
            return 1
        emit({"lang": detect_lang(text)})
        return 0
    if tool == "lint":
        from clair_toolkit.outbound import lint

        if args.text is not None:
            text = args.text
        elif args.text_file:
            text = Path(args.text_file).read_text(encoding="utf-8")
        else:
            emit({"ok": False, "error": "missing_text"})
            return 1
        emit(
            lint(
                text,
                args.channel,
                thread_lang=args.thread_lang,
                follow_up=args.follow_up,
                first_of_day=args.first_of_day,
                deny=args.deny,
                deny_file=Path(args.deny_file) if args.deny_file else None,
            )
        )
        return 0
    if tool == "dedupe":
        from clair_toolkit.dedupe import dedupe, load_contacts

        emit(dedupe(load_contacts(Path(args.path)), args.email))
        return 0
    if tool == "labels":
        from clair_toolkit.labels import check_path

        emit(check_path(Path(args.path)))
        return 0
    if tool == "cleanup":
        from clair_toolkit.cleanup import plan_path

        queues = [Path(item) for item in (args.queue or [])]
        emit(plan_path(Path(args.path), Path(args.state), args.ours, queues))
        return 0
    if tool == "handoff":
        from clair_toolkit.handoff import build_path

        emit(build_path(Path(args.path)))
        return 0
    emit({"ok": False, "error": "unknown_tool"})
    return 2


if __name__ == "__main__":
    sys.exit(main())
