"""Owner routing shared by the classifier and the handoff tool."""

from __future__ import annotations

import re

HR_RE = re.compile(
    r"\bsgk\b|\bssk\b|bordro|maa[sş]|salary|payroll|[oö]zl[uü]k|"
    r"insan kaynaklar[ıi]|i[sş]e giri[sş]|i[sş]ten [cç][ıi]k[ıi][sş]|\bpersonel\b",
    re.I,
)
INVOICE_NO_RE = re.compile(r"\b[A-Z][A-Z0-9]{2}\d{13}\b")
INVOICE_WORD_RE = re.compile(
    r"e-?\s?fatura|e-?\s?ar[sş]iv|\birsaliye\b|\bfatura\b|invoice no|fatura no",
    re.I,
)
PAYMENT_RE = re.compile(
    r"payment confirmation|payment received|[oö]deme teyid|[oö]deme onay|"
    r"\bdekont\b|\bhavale\b|\btahsilat\b|paid in full",
    re.I,
)
DELIVERY_RE = re.compile(
    r"\bdelivery\b|teslimat|teslim ald|goods reception|mal kabul|gelen mal|sevkiyat|\bsevk\b",
    re.I,
)
SUPPLIER_RE = re.compile(r"\bsupplier\b|tedarik[cç]i", re.I)
CLAIR_RE = re.compile(
    r"operasyon|operational|g[uü]nl[uü]k m[uü][sş]teri|daily customer|"
    r"confirmed customer|m[uü][sş]teri teyit",
    re.I,
)
DECLINE_RE = re.compile(
    r"not interested|no thank you|we decline|politely decline|"
    r"ilgilenmiyoruz|ilgilenmiyorum|uygun de[gğ]il|vazge[cç]",
    re.I,
)


def invoice_signal(text: str) -> bool:
    return bool(INVOICE_NO_RE.search(text or "") or INVOICE_WORD_RE.search(text or ""))


def route(category: str, text: str) -> tuple[str, str | None]:
    """Return (owner, rule). NONE means archive, not a handoff."""
    text = text or ""
    if category == "notification":
        return "NONE", "notifications -> archive"
    if category == "HR-SGK" or HR_RE.search(text):
        return "Christina", "staff/HR/SGK/salary -> Christina"
    if category == "bounce":
        return "Catalina", "bounces -> Catalina"
    if category == "auto-reply":
        return "Catalina", "auto-replies -> Catalina"
    if category == "cold-reply":
        return "Catalina", "prospect/cold replies -> Catalina"
    if category == "invoice" or invoice_signal(text):
        return "Vega", "supplier invoices / e-fatura -> Vega"
    if category == "business" and DECLINE_RE.search(text):
        return "Catalina", "prospect declines -> Catalina"
    if PAYMENT_RE.search(text):
        return "Vega", "payment confirmation -> Vega"
    if DELIVERY_RE.search(text):
        return "Vega", "delivery / goods reception -> Vega"
    if SUPPLIER_RE.search(text):
        return "Vega", "supplier mail -> Vega"
    if CLAIR_RE.search(text):
        return "Clair", "operational/confirmed-customer -> Clair"
    return "UNKNOWN", None
