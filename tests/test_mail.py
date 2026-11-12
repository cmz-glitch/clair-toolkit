import json

from tests.support import load_out, run_tool

OURS = "ops@entegrepack.com"


def _write(tmp_path, name, payload):
    path = tmp_path / name
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_gate_safe_block_and_waiting_reply(tmp_path):
    safe = _write(
        tmp_path,
        "safe.json",
        {
            "id": "thread-aaa-1111",
            "labelIds": ["INBOX"],
            "messages": [
                {
                    "id": "m1",
                    "from": "Ada <ada@buyer.example>",
                    "date": "2026-11-11T08:00:00+00:00",
                    "subject": "Carton size",
                    "labelIds": ["INBOX"],
                }
            ],
        },
    )
    got = load_out(run_tool("gate", safe, "--ours", OURS, "--now", "2026-11-12T08:00:00+00:00"))
    assert got == {"verdict": "SAFE_TO_REPLY", "reason": "open", "waiting_reply": False}

    replied = _write(
        tmp_path,
        "replied.json",
        {
            "labelIds": ["INBOX", "Label_9"],
            "messages": [
                {
                    "from": "Ada <ada@buyer.example>",
                    "date": "2026-11-11T08:00:00+00:00",
                    "labelIds": ["INBOX"],
                },
                {
                    "from": "Clair <ops@entegrepack.com>",
                    "date": "2026-11-11T09:00:00+00:00",
                    "labelIds": ["SENT"],
                },
            ],
        },
    )
    got = load_out(run_tool("gate", replied, "--ours", OURS, "--now", "2026-11-12T08:00:00+00:00"))
    assert got["verdict"] == "BLOCK"
    assert got["reason"] == "already_replied"
    assert got["waiting_reply"] is True

    archived = _write(
        tmp_path,
        "arch.json",
        {
            "labelIds": ["Label_1"],
            "messages": [
                {"from": "Ada <ada@buyer.example>", "date": "2026-11-11T08:00:00+00:00", "labelIds": ["Label_1"]}
            ],
        },
    )
    got = load_out(run_tool("gate", archived, "--ours", OURS, "--now", "2026-11-12T08:00:00+00:00"))
    assert got["reason"] == "archived"

    final = _write(
        tmp_path,
        "final.json",
        {
            "finalized": True,
            "labelIds": ["INBOX"],
            "messages": [
                {"from": "Ada <ada@buyer.example>", "date": "2026-11-11T08:00:00+00:00", "labelIds": ["INBOX"]}
            ],
        },
    )
    assert load_out(run_tool("gate", final, "--ours", OURS))["reason"] == "finalized"

    stale = _write(
        tmp_path,
        "stale.json",
        {
            "labelIds": ["INBOX"],
            "messages": [
                {"from": "Ada <ada@buyer.example>", "date": "2026-11-01T08:00:00+00:00", "labelIds": ["INBOX"]}
            ],
        },
    )
    assert (
        load_out(run_tool("gate", stale, "--ours", OURS, "--now", "2026-11-10T08:00:00+00:00"))["reason"]
        == "stale"
    )
    exact = load_out(run_tool("gate", stale, "--ours", OURS, "--now", "2026-11-08T08:00:00+00:00"))
    assert exact["verdict"] == "SAFE_TO_REPLY"
    short = load_out(
        run_tool("gate", safe, "--ours", OURS, "--days", "0.5", "--now", "2026-11-12T08:00:00+00:00")
    )
    assert short["reason"] == "stale"


def test_sent_duplicate_address_domain_and_filters(tmp_path):
    path = _write(
        tmp_path,
        "sent.json",
        [
            {
                "id": "s1",
                "to": "Ada <ada@acme.example>",
                "cc": "",
                "date": "2026-11-01",
                "subject": "Intro packing boxes",
                "snippet": "hello widgets",
            },
            {
                "id": "s2",
                "to": "else@gmail.com",
                "subject": "Intro packing boxes",
                "snippet": "hello",
            },
        ],
    )
    address = load_out(
        run_tool("sent-dup", path, "--to", "ada@acme.example", "--subject", "Intro packing", "--keyword", "widgets")
    )
    assert address["hit"] is True
    assert address["matches"][0]["via"] == "address"
    domain = load_out(run_tool("sent-dup", path, "--to", "other@acme.example", "--keyword", "widgets"))
    assert domain["matches"][0]["via"] == "domain"
    freemail = load_out(run_tool("sent-dup", path, "--to", "new@gmail.com"))
    assert freemail["hit"] is False
    missed = load_out(
        run_tool("sent-dup", path, "--to", "ada@acme.example", "--subject", "Unrelated offer")
    )
    assert missed["hit"] is False


def test_bounce_parser_and_classifier(tmp_path):
    quota = tmp_path / "quota.txt"
    quota.write_text(
        "Final-Recipient: rfc822; ada@full.example\n"
        "Diagnostic-Code: smtp; 552 5.2.2 Mailbox full\n",
        encoding="utf-8",
    )
    parsed = load_out(run_tool("bounce", quota))
    assert parsed["failed_address"] == "ada@full.example"
    assert parsed["smtp_code"] == "552"
    assert parsed["reason"] == "over_quota"

    missing = tmp_path / "missing.txt"
    missing.write_text("<ada@missing.example>: host mx said: 550 5.1.1 No such user\n", encoding="utf-8")
    parsed = load_out(run_tool("bounce", missing))
    assert parsed["failed_address"] == "ada@missing.example"
    assert parsed["reason"] == "no_such_user"

    gone = tmp_path / "gone.txt"
    gone.write_text("<ada@gone.example>: Host not found, domain not found\n", encoding="utf-8")
    assert load_out(run_tool("bounce", gone))["reason"] == "domain_not_found"

    invoice = _write(
        tmp_path,
        "invoice.json",
        {
            "id": "m-inv",
            "threadId": "thread-inv",
            "from": "Billing <noreply@efatura.example>",
            "to": OURS,
            "date": "2026-11-11T08:03:00+00:00",
            "subject": "e-Fatura ORN2026000001420",
            "snippet": "Fatura ektedir",
            "labelIds": ["INBOX"],
        },
    )
    got = load_out(run_tool("classify", invoice, "--ours", OURS))
    assert got["category"] == "invoice"
    assert got["owner"] == "Vega"
    assert "Label_1" in got["labels_add"]
    assert "INBOX" in got["labels_remove"]
    assert got["archive"] is True

    bounce = _write(
        tmp_path,
        "bounce.json",
        {
            "id": "m-b",
            "threadId": "thread-b",
            "from": "Mail Delivery Subsystem <mailer-daemon@googlemail.com>",
            "date": "2026-11-11T08:03:00+00:00",
            "subject": "Delivery Status Notification (Failure)",
            "body": "Final-Recipient: rfc822; ada@full.example\n552 mailbox full\n",
            "labelIds": ["INBOX"],
        },
    )
    got = load_out(run_tool("classify", bounce, "--ours", OURS))
    assert got["category"] == "bounce"
    assert got["owner"] == "Catalina"
    assert got["bounce"]["failed_address"] == "ada@full.example"
    assert got["archive"] is True

    auto = _write(
        tmp_path,
        "auto.json",
        {
            "from": "Ada <ada@buyer.example>",
            "subject": "Automatic reply: out of office",
            "snippet": "I am currently out of the office",
            "labelIds": ["INBOX", "Label_12"],
            "date": "2026-11-11T08:00:00Z",
        },
    )
    assert load_out(run_tool("classify", auto))["category"] == "auto-reply"

    cold = _write(
        tmp_path,
        "cold.json",
        {
            "id": "m-c",
            "threadId": "thread-c",
            "from": "Ada <ada@prospect.example>",
            "date": "2026-11-11T08:03:00+00:00",
            "subject": "Re: introduction",
            "snippet": "Send a catalogue",
            "labelIds": ["INBOX", "Label_12"],
        },
    )
    got = load_out(run_tool("classify", cold, "--ours", OURS))
    assert got["category"] == "cold-reply"
    assert got["owner"] == "Catalina"
    assert "Label_13" in got["labels_add"]
    assert "Label_12" in got["labels_remove"]
    assert "Label_9" not in got["labels_add"]

    hr = _write(
        tmp_path,
        "hr.json",
        {
            "from": "Insan <hr@ornek.example>",
            "subject": "SGK bildirim",
            "body": "Mayis SGK bordro ektedir",
            "labelIds": ["INBOX"],
            "date": "2026-11-11T08:00:00Z",
        },
    )
    assert load_out(run_tool("classify", hr))["owner"] == "Christina"
    assert load_out(run_tool("classify", hr))["category"] == "HR-SGK"

    note = _write(
        tmp_path,
        "note.json",
        {
            "from": "News <noreply@lists.example>",
            "subject": "Weekly newsletter",
            "snippet": "Unsubscribe here",
            "labelIds": ["INBOX"],
            "date": "2026-11-11T08:00:00Z",
        },
    )
    note_got = load_out(run_tool("classify", note))
    assert note_got["category"] == "notification"
    assert note_got["archive"] is True

    business = _write(
        tmp_path,
        "biz.json",
        {
            "from": "Ada <ada@buyer.example>",
            "subject": "Question about the print file",
            "body": "Can you resend the print file today? We are waiting on it. Thanks.",
            "labelIds": ["INBOX"],
            "date": "2026-11-11T08:00:00Z",
        },
    )
    biz = load_out(run_tool("classify", business, "--ours", OURS))
    assert biz["category"] == "business"
    assert biz["owner"] == "UNKNOWN"
    assert "Label_4" in biz["labels_add"]

    thanks = _write(
        tmp_path,
        "thanks.json",
        {
            "from": "Ada <ada@buyer.example>",
            "subject": "Re: carton size",
            "body": "The size is 40 by 30 by 20.",
            "labelIds": ["INBOX", "Label_9"],
            "date": "2026-11-11T08:00:00Z",
        },
    )
    thank = load_out(run_tool("classify", thanks, "--ours", OURS))
    assert thank["action"] == "thank_you"
    assert thank["owner"] == "Clair"
    assert "Label_9" in thank["labels_remove"]
    assert "Label_4" not in thank["labels_add"]


def test_language_detector():
    samples = {
        "TR": "Merhaba, fatura icin tesekkur ederim. Lutfen koli adedini teyit eder misiniz?",
        "EN": "Hello, please confirm the quantity on the invoice. We need it today.",
        "FR": "Bonjour, merci pour votre message. Nous confirmons la commande.",
        "AR": "مرحبا، يرجى تأكيد الفاتورة",
        "ZH": "您好，请确认发票数量。",
    }
    for lang, text in samples.items():
        path_text = text
        proc = run_tool("lang", "--text", path_text)
        assert load_out(proc) == {"lang": lang}
    assert load_out(run_tool("lang", "--text", "..."))["lang"] == "unknown"


def test_outbound_linter(tmp_path):
    ok = tmp_path / "ok.txt"
    ok.write_text(
        "Hello,\n\nPlease confirm the carton quantity.\nWe need the photo today.\nThe file is attached.\n\nClair\n+90 212 000 00 00\n",
        encoding="utf-8",
    )
    assert load_out(run_tool("lint", "--channel", "email", "--thread-lang", "EN", "--text-file", ok)) == {
        "verdict": "PASS",
        "reasons": [],
    }
    morning = tmp_path / "morning.txt"
    morning.write_text(
        "Good morning,\n\nPlease confirm the carton quantity.\nWe need the photo today.\nThe file is attached.\n\n+90 212 000 00 00\n",
        encoding="utf-8",
    )
    reasons = load_out(run_tool("lint", "--channel", "email", "--thread-lang", "EN", "--text-file", morning))
    assert reasons["verdict"] == "FAIL"
    assert any(item.startswith("G:") for item in reasons["reasons"])

    ps = ok.read_text(encoding="utf-8") + "\nPS: also send the swatch\n"
    ps_path = tmp_path / "ps.txt"
    ps_path.write_text(ps, encoding="utf-8")
    ps_out = load_out(run_tool("lint", "--channel", "email", "--thread-lang", "EN", "--text-file", ps_path))
    assert any(item.startswith("PS:") for item in ps_out["reasons"])

    dubai = tmp_path / "dubai.txt"
    dubai.write_text(
        "Hello,\n\nHe is in Dubai this week.\nPlease confirm the carton quantity.\nThe file is attached.\n\n+90 212 000 00 00\n",
        encoding="utf-8",
    )
    dubai_out = load_out(run_tool("lint", "--channel", "email", "--thread-lang", "EN", "--text-file", dubai))
    assert any(item.startswith("C:") and "dubai" in item for item in dubai_out["reasons"])

    jayden = tmp_path / "jayden.txt"
    jayden.write_text(
        "Hello,\n\nJayden sent the sample price.\nPlease ignore that number.\nThe file is attached.\n\n+90 212 000 00 00\n",
        encoding="utf-8",
    )
    jayden_out = load_out(run_tool("lint", "--channel", "email", "--thread-lang", "EN", "--text-file", jayden))
    assert any(item.startswith("B:") and "jayden" in item for item in jayden_out["reasons"])

    po = tmp_path / "po.txt"
    po.write_text(
        "Hello,\n\nPlease see CO2610-0139 for the lines.\nWe need the photo today.\nThe file is attached.\n\n+90 212 000 00 00\n",
        encoding="utf-8",
    )
    po_out = load_out(run_tool("lint", "--channel", "email", "--thread-lang", "EN", "--text-file", po))
    assert any("PO or CO" in item for item in po_out["reasons"])

    short = tmp_path / "short.txt"
    short.write_text("Hello. Please confirm the quantity today.\n\n+90 212 000 00 00\n", encoding="utf-8")
    short_out = load_out(run_tool("lint", "--channel", "email", "--thread-lang", "EN", "--text-file", short))
    assert any(item.startswith("LEN:") for item in short_out["reasons"])
    follow = load_out(
        run_tool("lint", "--channel", "email", "--thread-lang", "EN", "--follow-up", "--text-file", short)
    )
    assert follow["verdict"] == "PASS"

    mismatch = tmp_path / "tr.txt"
    mismatch.write_text(
        "Merhaba,\n\nKoli olcusu 40x30x20 cm.\nTeyit eder misiniz?\nTesekkur ederim.\n\n+90 212 000 00 00\n",
        encoding="utf-8",
    )
    mismatch_out = load_out(run_tool("lint", "--channel", "email", "--thread-lang", "EN", "--text-file", mismatch))
    assert any(item.startswith("F:") for item in mismatch_out["reasons"])
    missing_lang = load_out(run_tool("lint", "--channel", "email", "--text-file", ok))
    assert any("thread language missing" in item for item in missing_lang["reasons"])

    wa = load_out(
        run_tool(
            "lint",
            "--channel",
            "whatsapp",
            "--thread-lang",
            "TR",
            "--first-of-day",
            "--text",
            "Merhaba. Koli olcusu 40x30x20 cm. Teyit eder misiniz?",
        )
    )
    assert wa["verdict"] == "PASS"
    later = load_out(
        run_tool(
            "lint",
            "--channel",
            "whatsapp",
            "--thread-lang",
            "TR",
            "--text",
            "Koli olcusu 40x30x20 cm. Teyit eder misiniz? Tesekkurler.",
        )
    )
    assert later["verdict"] == "PASS"
    wa_hello = load_out(
        run_tool(
            "lint",
            "--channel",
            "whatsapp",
            "--thread-lang",
            "TR",
            "--first-of-day",
            "--text",
            "Hello. Please confirm the carton today. Thanks a lot.",
        )
    )
    assert any(item.startswith("G:") for item in wa_hello["reasons"])
    signed = load_out(
        run_tool(
            "lint",
            "--channel",
            "whatsapp",
            "--thread-lang",
            "TR",
            "--first-of-day",
            "--text",
            "Merhaba. Koli hazir. Yarin cikar.\n\nClair\n+90 212 000 00 00",
        )
    )
    assert any(item.startswith("I:") for item in signed["reasons"])
    no_phone = load_out(
        run_tool(
            "lint",
            "--channel",
            "email",
            "--thread-lang",
            "EN",
            "--text",
            "Hello,\n\nPlease confirm the carton quantity.\nWe need the photo today.\nThe file is attached.\n",
        )
    )
    assert any(item.startswith("I:") for item in no_phone["reasons"])


def test_dedupe_and_label_sanity(tmp_path):
    contacts = tmp_path / "contacts.txt"
    contacts.write_text("ada@acme.example\n# note\nx@gmail.com\n", encoding="utf-8")
    got = load_out(
        run_tool(
            "dedupe",
            contacts,
            "--email",
            "ada@acme.example",
            "--email",
            "other@acme.example",
            "--email",
            "y@gmail.com",
            "--email",
            "x@gmail.com",
            "--email",
            "new@fresh.example",
        )
    )
    assert got["new"] == ["y@gmail.com", "new@fresh.example"]
    vias = {item["email"]: item["via"] for item in got["skip"]}
    assert vias["ada@acme.example"] == "address"
    assert vias["other@acme.example"] == "domain"
    assert vias["x@gmail.com"] == "address"

    threads = _write(
        tmp_path,
        "labels.json",
        [
            {"id": "t-cold", "labelIds": ["Cold Mails", "Waiting Reply"]},
            {"id": "t-need", "labelIds": ["Label_4"]},
            {"id": "t-inv", "labelIds": ["INBOX", "Label_1"]},
            {"id": "t-ok", "labelIds": ["INBOX", "Label_4"]},
        ],
    )
    flags = load_out(run_tool("labels", threads))["flags"]
    rules = {(item["id"], item["rule"]) for item in flags}
    assert ("t-cold", "cold_and_waiting") in rules
    assert ("t-need", "need_attention_archived") in rules
    assert ("t-inv", "invoice_not_archived") in rules
    assert all(item["id"] != "t-ok" for item in flags)
