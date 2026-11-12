import json

from tests.conftest import load_out, run_tool

OURS = "ops@entegrepack.com"


def _threads():
    return [
        {
            "id": "thread-need",
            "labelIds": ["INBOX", "Label_4"],
            "last_from": "Ada <ada@buyer.example>",
            "last_date": "2026-11-12T08:00:00+04:00",
            "subject": "Question about the print file",
            "snippet": "Can you resend it",
        },
        {
            "id": "thread-answered",
            "labelIds": ["INBOX", "Label_4"],
            "last_from": "Clair <ops@entegrepack.com>",
            "last_date": "2026-11-12T09:00:00+04:00",
            "subject": "Re: print file",
            "snippet": "Hello, the file is attached",
        },
        {
            "id": "thread-queue",
            "labelIds": ["INBOX", "Label_12"],
            "last_from": "Clair <ops@entegrepack.com>",
            "subject": "Intro",
            "snippet": "Hello",
        },
        {
            "id": "thread-handled",
            "labelIds": ["INBOX", "Label_4"],
            "last_from": "Ada <ada@buyer.example>",
            "subject": "Old note",
            "snippet": "fyi",
        },
        {
            "id": "thread-invoice",
            "labelIds": ["INBOX", "Label_1", "Label_4"],
            "last_from": "Billing <noreply@efatura.example>",
            "subject": "e-fatura",
            "snippet": "Fatura ektedir",
        },
        {
            "id": "thread-bounce",
            "labelIds": ["INBOX"],
            "last_from": "Mail Delivery Subsystem <mailer-daemon@googlemail.com>",
            "subject": "Delivery Status Notification",
            "snippet": "552 mailbox full ada@full.example",
        },
        {
            "id": "thread-auto",
            "labelIds": ["INBOX"],
            "last_from": "Ada <ada@buyer.example>",
            "subject": "Automatic reply: out of office",
            "snippet": "I am currently out",
        },
        {
            "id": "thread-wait",
            "labelIds": ["INBOX", "Label_9"],
            "last_from": "Clair <ops@entegrepack.com>",
            "subject": "Re: quote",
            "snippet": "Hello, following up",
        },
        {
            "id": "thread-cold",
            "labelIds": ["INBOX", "Label_12", "Label_9"],
            "last_from": "Clair <ops@entegrepack.com>",
            "subject": "Intro",
            "snippet": "Hello",
        },
        {
            "id": "thread-news",
            "labelIds": ["INBOX", "Label_4"],
            "last_from": "News <noreply@lists.example>",
            "subject": "Weekly newsletter",
            "snippet": "Unsubscribe",
        },
    ]


def test_cleanup_plan_keeps_only_open_work(tmp_path):
    threads = tmp_path / "inbox.json"
    threads.write_text(json.dumps(_threads()), encoding="utf-8")
    state = tmp_path / "cycle_state.json"
    state.write_text(
        json.dumps({"handled_thread_ids": {"thread-handled": "already done"}, "handled_message_ids": []}),
        encoding="utf-8",
    )
    queue = tmp_path / "clair.md"
    queue.write_text(
        "- [ ] 2026-11-11 10:00 | Clair | wait on sample | thread-queue\n"
        "- [x] 2026-11-11 10:00 | Clair | closed | thread-cold\n",
        encoding="utf-8",
    )
    got = load_out(
        run_tool(
            "cleanup",
            threads,
            "--state",
            state,
            "--ours",
            OURS,
            "--queue",
            queue,
        )
    )
    by_id = {row["id"]: row for row in got["plan"]}
    assert by_id["thread-need"] == {"id": "thread-need", "action": "KEEP", "reason": "need_attention_unanswered"}
    assert by_id["thread-queue"]["action"] == "KEEP"
    assert by_id["thread-queue"]["reason"] == "open_queue"
    assert by_id["thread-answered"]["action"] == "ARCHIVE"
    assert by_id["thread-answered"]["reason"] == "answered"
    assert by_id["thread-handled"]["reason"] == "handled"
    assert by_id["thread-invoice"]["reason"] == "invoice_filed"
    assert by_id["thread-bounce"]["reason"] == "bounce"
    assert by_id["thread-auto"]["reason"] == "auto_reply"
    assert by_id["thread-wait"]["reason"] == "waiting_reply"
    assert by_id["thread-cold"]["reason"] == "cold_mail"
    assert by_id["thread-news"]["reason"] == "notification"
    assert "thread-need" not in got["archive_ids"]
    assert "thread-queue" not in got["archive_ids"]
    assert set(got["archive_ids"]) == {
        "thread-answered",
        "thread-handled",
        "thread-invoice",
        "thread-bounce",
        "thread-auto",
        "thread-wait",
        "thread-cold",
        "thread-news",
    }
    fixes = {item["id"]: item for item in got["label_fixes"]}
    assert "Label_4" in fixes["thread-answered"]["remove"]
    assert fixes["thread-answered"]["reason"] == "reply_is_last"
    assert "Label_9" in fixes["thread-cold"]["remove"]
    assert "Label_12" not in fixes["thread-cold"]["remove"]
    assert "thread-wait" not in fixes or "Label_9" not in fixes["thread-wait"]["remove"]
    assert "delete" not in json.dumps(got)


def test_handoff_is_silent_and_routes(tmp_path):
    cold = {
        "category": "cold-reply",
        "owner": "Catalina",
        "rule": "prospect/cold replies -> Catalina",
        "from": "Ada <ada@prospect.example>",
        "date": "2026-11-11T08:03:00+00:00",
        "subject": "Re: introduction",
        "snippet": "Send a catalogue",
        "ask": "introduction — Send a catalogue",
        "thread_id": "thread-c",
        "message_id": "m-c",
        "labels": ["INBOX", "Label_12"],
        "labels_add": ["Label_13"],
        "labels_remove": ["Label_12", "Label_9"],
        "sent": False,
    }
    path = tmp_path / "cold.json"
    path.write_text(json.dumps(cold), encoding="utf-8")
    got = load_out(run_tool("handoff", path))
    assert got["owner"] == "Catalina"
    assert got["ask_owner"] is False
    lines = got["handoff"].splitlines()
    assert lines[0] == "Rule: prospect/cold replies -> Catalina (Clair routing; silent handoff t532u)"
    assert "From: Ada <ada@prospect.example>" in lines
    assert "Date: 2026-11-11 12:03 Dubai" in lines
    assert "Thread: thread-c" in lines
    assert "Msg: m-c" in lines
    assert "Labels: Label_13" in lines
    assert "Sent: no" in lines
    assert "Milou" not in got["handoff"]
    assert "draft" not in got["handoff"].casefold()
    assert not any(line.lower().startswith("please") for line in lines)

    invoice = tmp_path / "inv.json"
    invoice.write_text(
        json.dumps(
            {
                "category": "invoice",
                "from": "Billing <noreply@efatura.example>",
                "date": "2026-11-11T08:03:00+00:00",
                "subject": "e-Fatura ORN2026000001420",
                "thread_id": "thread-inv",
                "message_id": "m-inv",
                "labels_add": ["Label_1"],
                "sent": False,
            }
        ),
        encoding="utf-8",
    )
    inv = load_out(run_tool("handoff", invoice))
    assert inv["owner"] == "Vega"
    assert inv["handoff"].startswith(
        "Rule: supplier invoices / e-fatura -> Vega (Clair routing; silent handoff t532u)"
    )

    decline = tmp_path / "no.json"
    decline.write_text(
        json.dumps(
            {
                "category": "business",
                "from": "Ada <ada@prospect.example>",
                "date": "2026-11-11T10:00:00+04:00",
                "subject": "Re: introduction",
                "text": "We are not interested in the range.",
                "thread_id": "thread-no",
                "message_id": "m-no",
            }
        ),
        encoding="utf-8",
    )
    assert load_out(run_tool("handoff", decline))["owner"] == "Catalina"
    assert "prospect declines -> Catalina" in load_out(run_tool("handoff", decline))["handoff"]

    delivery = tmp_path / "del.json"
    delivery.write_text(
        json.dumps(
            {
                "category": "business",
                "from": "Depot <depot@ornek.example>",
                "date": "2026-11-12T06:00:00+00:00",
                "subject": "Goods reception",
                "text": "Goods reception completed for the cartons today.",
                "thread_id": "thread-del",
                "message_id": "m-del",
            }
        ),
        encoding="utf-8",
    )
    assert "delivery / goods reception -> Vega" in load_out(run_tool("handoff", delivery))["handoff"]

    pay = tmp_path / "pay.json"
    pay.write_text(
        json.dumps(
            {
                "category": "business",
                "from": "Ada <ada@buyer.example>",
                "subject": "Transfer",
                "text": "Payment confirmation: dekont is attached.",
                "date": "2026-11-12T06:00:00+00:00",
                "thread_id": "thread-pay",
                "message_id": "m-pay",
            }
        ),
        encoding="utf-8",
    )
    assert load_out(run_tool("handoff", pay))["owner"] == "Vega"

    hr = tmp_path / "hr.json"
    hr.write_text(
        json.dumps(
            {
                "category": "HR-SGK",
                "from": "Insan <hr@ornek.example>",
                "subject": "SGK",
                "date": "2026-11-12T06:00:00+00:00",
                "thread_id": "thread-hr",
                "message_id": "m-hr",
            }
        ),
        encoding="utf-8",
    )
    assert load_out(run_tool("handoff", hr))["owner"] == "Christina"

    clair = tmp_path / "clair.json"
    clair.write_text(
        json.dumps(
            {
                "category": "business",
                "owner": "Clair",
                "rule": "operational/confirmed-customer -> Clair",
                "from": "Ada <ada@buyer.example>",
                "subject": "Gunluk musteri teyidi",
                "text": "Gunluk musteri teyidi: colour confirmed.",
                "date": "2026-11-12T06:00:00+00:00",
                "thread_id": "thread-op",
                "message_id": "m-op",
            }
        ),
        encoding="utf-8",
    )
    clair_got = load_out(run_tool("handoff", clair))
    assert clair_got["owner"] == "Clair"
    assert clair_got["handoff"] is None
    assert clair_got["ask_owner"] is False

    unknown = tmp_path / "unk.json"
    unknown.write_text(
        json.dumps(
            {
                "category": "business",
                "from": "Ada <ada@buyer.example>",
                "subject": "Room change",
                "text": "The meeting room changed to room 3.",
                "date": "2026-11-12T06:00:00+00:00",
                "thread_id": "thread-u",
                "message_id": "m-u",
            }
        ),
        encoding="utf-8",
    )
    unknown_got = load_out(run_tool("handoff", unknown))
    assert unknown_got["owner"] == "UNKNOWN"
    assert unknown_got["ask_owner"] is True
    assert unknown_got["handoff"] is None

    news = tmp_path / "news.json"
    news.write_text(
        json.dumps({"category": "notification", "from": "News <noreply@lists.example>", "subject": "Digest"}),
        encoding="utf-8",
    )
    news_got = load_out(run_tool("handoff", news))
    assert news_got["owner"] == "NONE"
    assert news_got["handoff"] is None
    assert news_got["ask_owner"] is False

    bounce = tmp_path / "b.json"
    bounce.write_text(
        json.dumps(
            {
                "category": "bounce",
                "from": "Mail Delivery <mailer-daemon@googlemail.com>",
                "date": "2026-11-11T08:03:00+00:00",
                "thread_id": "thread-b",
                "message_id": "m-b",
                "bounce": {"failed_address": "ada@full.example", "smtp_code": "552", "reason": "over_quota"},
            }
        ),
        encoding="utf-8",
    )
    bounce_got = load_out(run_tool("handoff", bounce))
    assert bounce_got["owner"] == "Catalina"
    assert "Bounce 552 over_quota for ada@full.example" in bounce_got["handoff"]
    assert "Milou" not in bounce_got["handoff"]
