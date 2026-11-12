import json

from clair_toolkit.cycle_state import add_no_followup, is_handled, mark_handled
from tests.conftest import load_out, run_tool


def test_queue_append_done_list_chase(tmp_path):
    path = tmp_path / "clair.md"
    path.write_text("# clair queue\n\nkeep this note\n", encoding="utf-8")
    first = run_tool(
        "queue",
        "append",
        path,
        "--from",
        "Clair",
        "--task",
        "chase the sample",
        "--ref",
        "thread-aaa-1111",
        "--at",
        "2026-11-11 11:00",
    )
    assert first.returncode == 0
    assert load_out(first)["appended"] is True
    again = run_tool(
        "queue",
        "append",
        path,
        "--from",
        "Clair",
        "--task",
        "chase the sample again",
        "--ref",
        "thread-aaa-1111",
        "--at",
        "2026-11-12 09:00",
    )
    assert load_out(again)["appended"] is False
    run_tool(
        "queue",
        "append",
        path,
        "--from",
        "Kaan",
        "--task",
        "other",
        "--ref",
        "thread-bbb-2222",
        "--at",
        "2026-11-11 10:00",
    )
    run_tool(
        "queue",
        "append",
        path,
        "--from",
        "Clair",
        "--task",
        "fresh",
        "--ref",
        "thread-ccc-3333",
        "--at",
        "2026-11-12 11:30",
    )
    text = path.read_text(encoding="utf-8")
    assert text.startswith("# clair queue\n")
    assert "keep this note" in text
    listed = load_out(run_tool("queue", "list", path))
    assert [item["ref"] for item in listed["open"]] == [
        "thread-aaa-1111",
        "thread-bbb-2222",
        "thread-ccc-3333",
    ]
    chase = load_out(
        run_tool("queue", "chase", path, "--hours", "24", "--bot", "Clair", "--now", "2026-11-12 12:00")
    )
    assert [item["ref"] for item in chase["chase"]] == ["thread-aaa-1111"]
    edge = load_out(
        run_tool("queue", "chase", path, "--hours", "25", "--bot", "Clair", "--now", "2026-11-12 12:00")
    )
    assert edge["chase"] == []
    done = load_out(run_tool("queue", "done", path, "--ref", "thread-aaa-1111"))
    assert done == {"updated": 1, "already_done": 0}
    again_done = load_out(run_tool("queue", "done", path, "--ref", "thread-aaa-1111"))
    assert again_done == {"updated": 0, "already_done": 1}
    assert "- [x] 2026-11-11 11:00 | Clair | chase the sample | thread-aaa-1111" in path.read_text(
        encoding="utf-8"
    )
    assert "keep this note" in path.read_text(encoding="utf-8")
    open_refs = [item["ref"] for item in load_out(run_tool("queue", "list", path))["open"]]
    assert "thread-aaa-1111" not in open_refs


def test_cycle_state_is_idempotent_and_keeps_other_keys(tmp_path):
    path = tmp_path / "cycle_state.json"
    path.write_text(
        json.dumps(
            {
                "last_cycle": "2026-10-16T05:59:29Z",
                "custom": {"keep": 1},
                "handled_thread_ids": {},
                "no_followup": [],
                "handled_message_ids": [],
            },
            indent=1,
        )
        + "\n",
        encoding="utf-8",
    )
    assert load_out(run_tool("cycle", "is-handled", path, "--thread", "thread-aaa-1111"))["handled"] is False
    assert load_out(
        run_tool(
            "cycle",
            "mark-handled",
            path,
            "--thread",
            "thread-aaa-1111",
            "--note",
            "promo, no action",
            "--message",
            "msg-111",
        )
    )["changed"] is True
    second = load_out(
        run_tool(
            "cycle",
            "mark-handled",
            path,
            "--thread",
            "thread-aaa-1111",
            "--note",
            "different note",
            "--message",
            "msg-111",
        )
    )
    assert second["changed"] is False
    data = json.loads(path.read_text(encoding="utf-8"))
    assert list(data)[:2] == ["last_cycle", "custom"]
    assert data["last_cycle"] == "2026-10-16T05:59:29Z"
    assert data["custom"] == {"keep": 1}
    assert data["handled_thread_ids"]["thread-aaa-1111"] == "promo, no action"
    assert data["handled_message_ids"] == ["msg-111"]
    seen = load_out(
        run_tool("cycle", "is-handled", path, "--thread", "thread-zzz-9999", "--message", "msg-111")
    )
    assert seen == {"handled": True, "no_followup": False, "via": "message"}
    added = add_no_followup(
        path,
        company="Ornek Cigars",
        email="info@ornekcigars.example",
        domain="ornekcigars.example",
        thread="thread-ddd-4444",
        reason="Polite decline",
        date="2026-11-01",
    )
    assert added["added"] is True
    duplicate = add_no_followup(
        path,
        company="Other",
        email="INFO@ornekcigars.example",
        domain="ornekcigars.example",
        thread="thread-eee-5555",
        reason="again",
        date="2026-11-02",
    )
    assert duplicate == {"added": False, "reason": "exists"}
    data = json.loads(path.read_text(encoding="utf-8"))
    assert len(data["no_followup"]) == 1
    assert data["custom"] == {"keep": 1}
    flagged = is_handled(path, "thread-ddd-4444")
    assert flagged["handled"] is False
    assert flagged["no_followup"] is True
