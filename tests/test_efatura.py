from pathlib import Path

from clair_toolkit.efatura import parse_invoice, parse_text, supplier_slug
from tests.support import load_out, run_tool
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


def test_minified_title_is_not_part_of_the_supplier(tmp_path):
    path = tmp_path / "min.html"
    path.write_text(
        "<html><head><title>e-Fatura</title></head><body><table><tr><td>"
        "ORNEK HIDROLIK LTD STI<br>VKN: 1234567890</td></tr></table>"
        "SAYIN<br>ALICI A.S.<br>VKN: 1098765432<br>"
        "Fatura No: ORN2026000001001<br>Fatura Tarihi: 01-11-2026<br>"
        "KDV Matrahı 10,00 TL<br>Hesaplanan KDV 2,00 TL<br>Ödenecek Tutar 12,00 TL"
        "</body></html>",
        encoding="utf-8",
    )
    data = parse_invoice(path, at="2026-11-12 08:00")
    assert data["supplier"] == "ORNEK HIDROLIK LTD STI"
    assert data["invoice_no"] == "ORN2026000001001"
    assert data["total"] == "12.00"


def test_utility_pdf_layout(tmp_path):
    """Electricity-style text: Fatura Sıra No, Fatura Dönemi, ÖdenecekTutar."""
    text = Path("tests/fixtures/invoice_utility.txt").read_text(encoding="utf-8")
    parsed = parse_text(text)
    assert parsed["invoice_no"] == "ORN2026000007777"
    assert parsed["date"] == "2026-11-11"
    assert parsed["total"] == "102.00"
    assert parsed["due_date"] == "2026-11-23"
    assert parsed["supplier"] == "ORNEK ENERJI PERAKENDE SATIS A.S"
    assert parsed["vkn"] == "1234567890"
    pdf = tmp_path / "utility.pdf"
    pdf.write_bytes(
        text_pdf(
            [
                "Ozellestirme No:TR1.2 Fatura Sira No:ORN2026000007777 Fatura Donemi:11 - 11 - 2026/11-2026",
                "ORNEK ENERJI PERAKENDE SATIS A.S",
                "VKN:1234567890",
                "Fatura Tutari 100,50TL",
                "OdenecekTutar",
                "102,00",
                "Son OdemeTarihi",
                "23 - 11 - 2026",
            ]
        )
    )
    data = parse_invoice(pdf, at="2026-11-12 08:00")
    assert data["invoice_no"] == "ORN2026000007777"
    assert data["date"] == "2026-11-11"
    assert data["total"] == "102.00"
    assert data["due_date"] == "2026-11-23"


def test_glued_payable_and_vade_note():
    parsed = parse_text(
        "\n".join(
            [
                "ORNEK KARGO A.S.",
                "VKN: 1234567890",
                "Fatura No: ORN2026000000001",
                "Fatura Tarihi:10-11-2026",
                "Mal Hizmet Toplam Tutarı10,00 TRY",
                "KDV Matrahı10,00 TRY",
                "Hesaplanan KDV(%20)2,00 TRY",
                "Ödenecek Tutar12,00 TRY",
                "Fatura vadesi 16.11.2026dir.",
            ]
        )
    )
    assert parsed["invoice_no"] == "ORN2026000000001"
    assert parsed["date"] == "2026-11-10"
    assert parsed["total"] == "12.00"
    assert parsed["due_date"] == "2026-11-16"


def test_edm_shell_is_not_an_invoice():
    proc = run_tool("efatura", SHELL)
    assert proc.returncode == 1
    assert load_out(proc)["error"] == "edm_shell"
