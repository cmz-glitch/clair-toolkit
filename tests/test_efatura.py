from pathlib import Path

from clair_toolkit.efatura import parse_invoice, parse_text, supplier_slug
from tests.conftest import load_out, run_tool
from tests.pdfutil import text_pdf

FIXTURE = Path("tests/fixtures/invoice_ornek.html")
SHELL = Path("tests/fixtures/edm_shell.html")


def test_html_invoice_fields_filename_and_queue_line():
    proc = run_tool(
        "efatura",
        FIXTURE,
        "--thread",
        "thread-aaa-1111",
        "--at",
        "2026-11-12 08:23",
    )
    assert proc.returncode == 0, proc.stderr
    data = load_out(proc)
    assert data["supplier"] == "ORNEK HIDROLIK SAN. VE TIC. LTD. STI."
    assert data["supplier_slug"] == "ORNEK_HIDROLIK"
    assert data["vkn"] == "1234567890"
    assert data["invoice_no"] == "ORN2026000001420"
    assert data["date"] == "2026-11-09"
    assert data["net"] == "2000.00"
    assert data["kdv"] == "400.00"
    assert data["total"] == "2400.00"
    assert data["currency"] == "TRY"
    assert data["due_date"] == "2026-11-23"
    assert data["lines"] == [
        {
            "no": 1,
            "description": "SLIDE TABLE",
            "qty": "2",
            "unit": "Adet",
            "unit_price": "1000.00",
            "kdv_rate": "20",
            "kdv": "400.00",
            "amount": "2000.00",
        }
    ]
    assert data["filename"] == "2026-11-09_ORNEK_HIDROLIK_ORN2026000001420.pdf"
    assert data["queue_line"] == (
        "- [ ] 2026-11-12 08:23 | Clair | Supplier e-fatura "
        "ORNEK HIDROLIK SAN. VE TIC. LTD. STI. ORN2026000001420 "
        "(09-11-2026, 2.000,00 + KDV 400,00 = 2.400,00 TRY, vade 23-11-2026) "
        "— PDF vega_invoices/2026-11-09_ORNEK_HIDROLIK_ORN2026000001420.pdf "
        "| ref thread thread-aaa-1111"
    )
    assert data["vkn"] != "1098765432"


def test_vade_note_and_slug_rules():
    parsed = parse_text(
        "\n".join(
            [
                "ORNEK HIDROLIK LTD STI",
                "VKN: 1234567890",
                "Fatura No: ORN2026000001999",
                "Fatura Tarihi: 11-11-2026",
                "KDV Matrahi 10,00 TL",
                "Hesaplanan KDV 2,00 TL",
                "Odenecek Tutar 12,00 TL",
                "vade 16-11-2026",
            ]
        )
    )
    assert parsed["due_date"] == "2026-11-16"
    assert parsed["invoice_no"] == "ORN2026000001999"
    assert supplier_slug("Yildiz Kargo A.S.") == "YILDIZ"
    assert supplier_slug("Anpa Gross Magazacilik") == "ANPA_GROSS"
    assert supplier_slug("CK Bogazici Elektrik") == "CK_BOGAZICI"
    assert supplier_slug("Sahin Ambalaj") == "SAHIN_AMBALAJ"


def test_pdf_invoice(tmp_path):
    path = tmp_path / "inv.pdf"
    path.write_bytes(
        text_pdf(
            [
                "ORNEK HIDROLIK SAN. VE TIC. LTD. STI.",
                "VKN: 1234567890",
                "SAYIN",
                "BUYER LTD STI",
                "VKN: 1098765432",
                "Fatura No: ORN2026000001420",
                "Fatura Tarihi: 09-11-2026",
                "Son Odeme Tarihi: 23-11-2026",
                "KDV Matrahi 2.000,00 TL",
                "Hesaplanan KDV 400,00 TL",
                "Odenecek Tutar 2.400,00 TL",
            ]
        )
    )
    data = parse_invoice(path, at="2026-11-12 08:23")
    assert data["invoice_no"] == "ORN2026000001420"
    assert data["vkn"] == "1234567890"
    assert data["total"] == "2400.00"
    assert data["due_date"] == "2026-11-23"
    assert data["filename"].endswith("_ORN2026000001420.pdf")


def test_edm_shell_is_not_an_invoice():
    proc = run_tool("efatura", SHELL)
    assert proc.returncode == 1
    assert load_out(proc)["error"] == "edm_shell"
