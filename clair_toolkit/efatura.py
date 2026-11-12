"""Parse a Turkish e-fatura HTML (GİB/EVA viewer) or PDF."""

from __future__ import annotations

import re
from decimal import Decimal
from html.parser import HTMLParser
from pathlib import Path

from clair_toolkit.util import (
    decode_bytes,
    format_tr_amount,
    money_str,
    now_dubai,
    parse_tr_amount,
)

LEGAL = frozenset(
    {
        "LTD",
        "STI",
        "AS",
        "SAN",
        "TIC",
        "VE",
        "SANAYI",
        "TICARET",
        "LIMITED",
        "SIRKETI",
        "ANONIM",
        "KOOP",
        "KOOPERATIF",
    }
)
GENERIC_LAST = frozenset(
    {
        "KARGO",
        "ELEKTRIK",
        "MAGAZACILIK",
        "LOJISTIK",
        "NAKLIYE",
        "NAKLIYAT",
        "GIDA",
        "INSAAT",
    }
)
_TR = str.maketrans(
    {
        "ç": "c",
        "Ç": "C",
        "ğ": "g",
        "Ğ": "G",
        "ı": "i",
        "İ": "I",
        "ö": "o",
        "Ö": "O",
        "ş": "s",
        "Ş": "S",
        "ü": "u",
        "Ü": "U",
    }
)

_INVOICE_NO = re.compile(r"Fatura\s*(?:No|Numaras[ıi])\s*:?\s*([A-Z][A-Z0-9]{2}\d{13})", re.I)
_INVOICE_DATE = re.compile(
    r"Fatura\s*Tarihi\s*:?\s*(\d{2})[-./](\d{2})[-./](\d{4})", re.I
)
_DUE = re.compile(
    r"(?:Son\s+[ÖO]deme\s+Tarihi|Vade\s+Tarihi|[ÖO]deme\s+Vadesi)\s*:?\s*"
    r"(\d{2})[-./](\d{2})[-./](\d{4})",
    re.I,
)
_DUE_NOTE = re.compile(
    r"(?:vade|son\s+[öo]deme)\s+(\d{2})[-./](\d{2})[-./](\d{4})", re.I
)
_VKN = re.compile(r"\bVKN\s*:?\s*(\d{10,11})", re.I)
_MONEY = re.compile(
    r"(\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2}|\d+\.\d{2})\s*(TL|TRY|USD|EUR|€|\$)?"
)
_META = re.compile(
    r"^(tel|fax|web|e-?posta|e-?mail|vergi|vkn|tckn|mersis|ticaret|adres)\b",
    re.I,
)
_MATRAH = re.compile(r"KDV\s*Matrah[ıi]\s*:?\s*", re.I)
_NET = re.compile(r"Mal\s+Hizmet\s+Toplam\s+Tutar[ıi]\s*:?\s*", re.I)
_KDV = re.compile(r"Hesaplanan\s+KDV(?:\s*\([^)]*\))?\s*:?\s*", re.I)
_PAY = re.compile(r"(?:Ö|O)denecek\s+Tutar\s*:?\s*", re.I)
_GROSS = re.compile(r"Vergiler\s+Dahil\s+Toplam\s+Tutar[ıi]\s*:?\s*", re.I)

_HEADER_KEYS = (
    ("mal hizmet tutari", "amount"),
    ("mal hizmet tutarı", "amount"),
    ("birim fiyat", "unit_price"),
    ("kdv orani", "kdv_rate"),
    ("kdv oranı", "kdv_rate"),
    ("kdv tutari", "kdv"),
    ("kdv tutarı", "kdv"),
    ("sira no", "no"),
    ("sıra no", "no"),
    ("mal hizmet", "description"),
    ("miktar", "qty"),
)


class EdmShell(Exception):
    pass


class NoInvoiceText(Exception):
    pass


class _Extractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.rows: list[list[str]] = []
        self._skip = 0
        self._cell: list[str] | None = None
        self._row: list[str] | None = None

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in {"script", "style"}:
            self._skip += 1
            return
        if self._skip:
            return
        if tag == "tr":
            self._row = []
        elif tag in {"td", "th"} and self._row is not None:
            self._cell = []
        elif tag == "br":
            if self._cell is not None:
                self._cell.append("\n")
            else:
                self.parts.append("\n")

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in {"script", "style"} and self._skip:
            self._skip -= 1
            return
        if self._skip:
            return
        if tag in {"td", "th"} and self._cell is not None:
            raw = "".join(self._cell)
            if self._row is not None:
                self._row.append(re.sub(r"\s+", " ", raw).strip())
            self.parts.append(raw)
            self.parts.append("\n")
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if any(self._row):
                self.rows.append(self._row)
            self._row = None
            self.parts.append("\n")
        elif tag in {"p", "div", "h1", "h2", "li", "table"}:
            self.parts.append("\n")

    def handle_data(self, data):
        if self._skip:
            return
        if self._cell is not None:
            self._cell.append(data)
        else:
            self.parts.append(data)


def html_parts(html: str) -> tuple[str, list[list[str]]]:
    parser = _Extractor()
    parser.feed(html)
    raw = "".join(parser.parts).replace("\xa0", " ")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in raw.splitlines()]
    compact: list[str] = []
    for line in lines:
        if line or (compact and compact[-1]):
            compact.append(line)
    return "\n".join(compact), parser.rows


def is_edm_shell(html: str) -> bool:
    low = html.casefold()
    if "fatura no" in low or "fatura tarihi" in low:
        return False
    return "edm" in low and ("iframe" in low or "myiframeid" in low)


def pdf_text(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise NoInvoiceText("pypdf_missing") from exc
    reader = PdfReader(str(path))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def supplier_slug(name: str) -> str:
    tokens = re.sub(r"[^A-Za-z0-9]+", " ", (name or "").translate(_TR)).upper().split()
    kept = [token for token in tokens if token not in LEGAL and len(token) > 1]
    if kept and kept[-1] in GENERIC_LAST:
        kept = kept[:-1]
    kept = kept[:3]
    return "_".join(kept) or "SUPPLIER"


def _money_after(pattern: re.Pattern, text: str):
    match = pattern.search(text)
    if not match:
        return None, None
    window = text[match.end() : match.end() + 80]
    found = _MONEY.search(window)
    if not found:
        return None, None
    return parse_tr_amount(found.group(1)), _currency(found.group(2))


def _currency(token: str | None) -> str | None:
    if not token:
        return None
    token = token.upper()
    if token in {"TL", "TRY"}:
        return "TRY"
    if token in {"USD", "$"}:
        return "USD"
    if token in {"EUR", "€"}:
        return "EUR"
    return token


def _iso_from_dmy(day: str, month: str, year: str) -> str:
    return f"{year}-{month}-{day}"


def _dmy(iso: str | None) -> str:
    if not iso:
        return ""
    year, month, day = iso.split("-")
    return f"{day}-{month}-{year}"


def _fold_header(text: str) -> str:
    text = text.replace("İ", "i").replace("I", "ı")
    text = text.casefold()
    text = text.translate(_TR)
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _header_map(cells: list[str]) -> dict[str, int] | None:
    mapping: dict[str, int] = {}
    folded = [_fold_header(cell) for cell in cells]
    if not any("mal hizmet" in cell or cell == "sira no" for cell in folded):
        return None
    for index, cell in enumerate(folded):
        for key, name in _HEADER_KEYS:
            if cell == key or cell.startswith(key):
                mapping.setdefault(name, index)
                break
    return mapping or None


def _cell_amount(cell: str) -> str | None:
    found = _MONEY.search(cell or "")
    if not found:
        return money_str(parse_tr_amount(cell))
    return money_str(parse_tr_amount(found.group(1)))


def _rate(cell: str) -> str | None:
    match = re.search(r"(\d+(?:[.,]\d+)?)", cell or "")
    if not match:
        return None
    amount = parse_tr_amount(match.group(1) if re.search(r"[.,]", match.group(1)) else match.group(1) + ",00")
    if amount is None:
        return None
    if amount == amount.to_integral():
        return str(amount.to_integral())
    return money_str(amount)


def _qty(cell: str) -> tuple[str | None, str | None]:
    match = re.match(r"([\d.,]+)\s*(.*)$", (cell or "").strip())
    if not match:
        return None, None
    amount = parse_tr_amount(match.group(1) if re.search(r"[.,]", match.group(1)) else match.group(1))
    qty = money_str(amount)
    if qty and qty.endswith(".00"):
        qty = qty[:-3]
    unit = match.group(2).strip() or None
    return qty, unit


def line_items(rows: list[list[str]]) -> list[dict]:
    mapping = None
    items = []
    for row in rows:
        if not row:
            continue
        maybe = _header_map(row)
        if maybe:
            mapping = maybe
            continue
        if not re.fullmatch(r"\d{1,3}", row[0].strip()):
            continue
        cols = mapping or {
            "no": 0,
            "description": 1,
            "qty": 2,
            "unit_price": 3,
            "kdv_rate": 6,
            "kdv": 7,
            "amount": 9 if len(row) > 9 else len(row) - 1,
        }

        def take(name: str) -> str:
            index = cols.get(name)
            if index is None or index >= len(row):
                return ""
            return row[index]

        qty, unit = _qty(take("qty"))
        item = {
            "no": int(row[0]),
            "description": take("description"),
            "qty": qty,
            "unit": unit,
            "unit_price": _cell_amount(take("unit_price")),
            "kdv_rate": _rate(take("kdv_rate")),
            "kdv": _cell_amount(take("kdv")),
            "amount": _cell_amount(take("amount")),
        }
        if item["description"]:
            items.append(item)
    return items


def _supplier_name(text: str) -> str | None:
    marker = re.search(r"\bSAYIN\b", text, re.I)
    head = text[: marker.start()] if marker else text
    for line in head.splitlines():
        line = line.strip(" -")
        if len(re.sub(r"[^A-Za-zÇĞİÖŞÜçğıöşü]", "", line)) < 3:
            continue
        if _META.match(line):
            continue
        if re.fullmatch(r"e-?\s*fatura", line, re.I):
            continue
        return re.sub(r"\s+", " ", line)
    return None


def _sum_kdv(text: str) -> tuple[Decimal | None, str | None]:
    total = Decimal("0")
    found = False
    currency = None
    for match in _KDV.finditer(text):
        window = text[match.end() : match.end() + 80]
        money = _MONEY.search(window)
        if not money:
            continue
        amount = parse_tr_amount(money.group(1))
        if amount is None:
            continue
        total += amount
        found = True
        currency = currency or _currency(money.group(2))
    if not found:
        return None, None
    return total.quantize(Decimal("0.01")), currency


def parse_text(text: str, rows: list[list[str]] | None = None) -> dict:
    number = _INVOICE_NO.search(text)
    date = _INVOICE_DATE.search(text)
    due = _DUE.search(text) or _DUE_NOTE.search(text)
    marker = re.search(r"\bSAYIN\b", text, re.I)
    head = text[: marker.start()] if marker else text
    vkns = _VKN.findall(head)
    net, net_cur = _money_after(_MATRAH, text)
    if net is None:
        net, net_cur = _money_after(_NET, text)
    kdv, kdv_cur = _sum_kdv(text)
    total, total_cur = _money_after(_PAY, text)
    if total is None:
        total, total_cur = _money_after(_GROSS, text)
    currency = total_cur or kdv_cur or net_cur or ("TRY" if re.search(r"\bTL\b", text) else None)
    supplier = _supplier_name(text)
    iso = _iso_from_dmy(*date.groups()) if date else None
    due_iso = _iso_from_dmy(*due.groups()) if due else None
    warnings = []
    if not supplier:
        warnings.append("missing_supplier")
    if not number:
        warnings.append("missing_invoice_no")
    if total is None:
        warnings.append("missing_total")
    payload = {
        "supplier": supplier,
        "supplier_slug": supplier_slug(supplier or ""),
        "vkn": vkns[0] if vkns else None,
        "invoice_no": number.group(1).upper() if number else None,
        "date": iso,
        "net": money_str(net),
        "kdv": money_str(kdv),
        "total": money_str(total),
        "currency": currency,
        "due_date": due_iso,
        "lines": line_items(rows or []),
    }
    if warnings:
        payload["warnings"] = warnings
    return payload


def filename_for(parsed: dict) -> str | None:
    if not parsed.get("date") or not parsed.get("invoice_no"):
        return None
    slug = parsed.get("supplier_slug") or "SUPPLIER"
    return f"{parsed['date']}_{slug}_{parsed['invoice_no']}.pdf"


def queue_line(parsed: dict, at: str, thread: str | None) -> str | None:
    if not parsed.get("invoice_no"):
        return None
    date = _dmy(parsed.get("date")) or "?"
    def tr(field: str) -> str:
        if not parsed.get(field):
            return "?"
        return format_tr_amount(Decimal(parsed[field]))

    vade = f", vade {_dmy(parsed['due_date'])}" if parsed.get("due_date") else ""
    name = parsed.get("supplier") or parsed.get("supplier_slug") or "SUPPLIER"
    pdf = filename_for(parsed) or (parsed["invoice_no"] + ".pdf")
    task = (
        f"Supplier e-fatura {name} {parsed['invoice_no']} "
        f"({date}, {tr('net')} + KDV {tr('kdv')} = {tr('total')} {parsed.get('currency') or 'TRY'}{vade}) "
        f"— PDF vega_invoices/{pdf}"
    )
    ref = f"ref thread {thread}" if thread else f"ref {parsed['invoice_no']}"
    return f"- [ ] {at} | Clair | {task} | {ref}"


def parse_invoice(path: Path, thread: str | None = None, at: str | None = None) -> dict:
    path = Path(path)
    raw = path.read_bytes()
    if raw.startswith(b"%PDF") or path.suffix.lower() == ".pdf":
        text = pdf_text(path)
        rows = None
        if not text.strip():
            raise NoInvoiceText("no_text")
    else:
        html = decode_bytes(raw)
        if is_edm_shell(html):
            raise EdmShell()
        text, rows = html_parts(html)
    parsed = parse_text(text, rows)
    stamp = at or now_dubai().strftime("%Y-%m-%d %H:%M")
    parsed["filename"] = filename_for(parsed)
    parsed["queue_line"] = queue_line(parsed, stamp, thread)
    return parsed
