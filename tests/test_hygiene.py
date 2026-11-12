from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Pieced together so this file does not contain the raw identifiers.
FORBIDDEN = (
    "2910798" + "264",
    "3361320" + "733",
    "7970053" + "078",
    "DPE2026" + "000001420",
    "SAH2026" + "000001111",
    "DL02026" + "000883852",
    "YKA2026" + "006387944",
    "E022026" + "000065261",
    "BEF2026" + "025120709",
    "denge" + "pnomatik",
    "aykut" + "@",
)


def test_repo_has_no_raw_upload_identifiers():
    hits = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in {".git", ".pytest_cache", "__pycache__"} for part in path.parts):
            continue
        text = path.read_bytes().decode("utf-8", "ignore")
        for token in FORBIDDEN:
            if token in text:
                hits.append(f"{path.relative_to(ROOT)}:{token}")
    assert hits == []
