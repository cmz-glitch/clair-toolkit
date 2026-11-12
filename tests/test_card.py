import json

from tests.support import run_tool


def test_four_options_are_a_valid_card():
    proc = run_tool(
        "card",
        "Book the sample invoice?",
        "Yes, go ahead",
        "Yes, but check the total",
        "Not now",
        "No",
    )
    assert proc.returncode == 0, proc.stderr
    card = json.loads(proc.stdout)
    widget = card["widget"]
    assert card["type"] == "widget"
    assert widget["allowCustom"] is True
    assert widget["multiSelect"] is True
    assert widget["options"][0]["style"] == "primary"
    assert [item["label"] for item in widget["options"]] == [
        "Yes, go ahead",
        "Yes, but check the total",
        "Not now",
        "No",
    ]


def test_three_options_are_a_broken_card():
    proc = run_tool("card", "Book the sample invoice?", "Yes", "Not now", "No")
    assert proc.returncode == 2
    assert "BROKEN CARD" in proc.stderr


def test_danger_marks_option_3():
    proc = run_tool(
        "card",
        "--danger",
        "3",
        "Book the sample invoice?",
        "Yes, go ahead",
        "Yes, but check the total",
        "No, drop it",
        "Not now",
    )
    assert proc.returncode == 0, proc.stderr
    options = json.loads(proc.stdout)["widget"]["options"]
    assert options[0]["style"] == "primary"
    assert options[2]["style"] == "danger"
    assert "style" not in options[1]
    assert "style" not in options[3]


def test_lint_rejects_an_other_option(tmp_path):
    path = tmp_path / "card.json"
    path.write_text(
        json.dumps(
            {
                "type": "widget",
                "widget": {
                    "prompt": "Book the sample invoice?",
                    "allowCustom": True,
                    "multiSelect": True,
                    "options": [
                        {"label": "Yes, go ahead", "style": "primary"},
                        {"label": "Not now"},
                        {"label": "No"},
                        {"label": "Other"},
                    ],
                },
            }
        ),
        encoding="utf-8",
    )
    proc = run_tool("card", "--lint", path)
    assert proc.returncode == 2
    assert "BROKEN CARD" in proc.stdout
    assert "Other" in proc.stdout
