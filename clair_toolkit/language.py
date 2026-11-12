"""Rule-only thread language: TR, EN, FR, AR, ZH."""

from __future__ import annotations

import re

_WORD = re.compile(r"[A-Za-zÀ-ÿĞğİıÖöŞşÜüÇç']+", re.UNICODE)

_TR = frozenset(
    """
    ve bir bu icin ile olan merhaba tesekkur tesekkurler lutfen fatura
    ederim degil var yok kadar sonra once cok gibi ama veya evet hayir
    iyi gunler siparis koli adet tutar teyit eder misiniz icin
    """.split()
)
_EN = frozenset(
    """
    the and to of for you your please hello thank thanks invoice we
    is are with this that from our need today confirm attached
    """.split()
)
_FR = frozenset(
    """
    le la les des vous nous bonjour merci pour avec une est pas dans
    facture cher votre commande message confirmons
    """.split()
)

_TR_CHARS = re.compile(r"[ğüşıöĞÜŞİÖ]")
_FR_CHARS = re.compile(r"[éèêëàùûôîïçÉÈÊËÀÙ]")


def _fold_token(token: str) -> str:
    table = str.maketrans(
        {
            "ç": "c",
            "Ç": "c",
            "ğ": "g",
            "Ğ": "g",
            "ı": "i",
            "İ": "i",
            "ö": "o",
            "Ö": "o",
            "ş": "s",
            "Ş": "s",
            "ü": "u",
            "Ü": "u",
            "é": "e",
            "è": "e",
            "ê": "e",
            "ë": "e",
            "à": "a",
            "ù": "u",
            "û": "u",
            "ô": "o",
            "î": "i",
            "ï": "i",
        }
    )
    return token.translate(table).casefold()


def detect_lang(text: str) -> str:
    text = text or ""
    arabic = len(re.findall(r"[\u0600-\u06FF]", text))
    chinese = len(re.findall(r"[\u4E00-\u9FFF]", text))
    if arabic >= 2 and arabic >= chinese:
        return "AR"
    if chinese >= 2 and chinese > arabic:
        return "ZH"
    scores = {"TR": 0, "EN": 0, "FR": 0}
    for token in _WORD.findall(text):
        folded = _fold_token(token)
        if folded in _TR:
            scores["TR"] += 1
        if folded in _EN:
            scores["EN"] += 1
        if folded in _FR:
            scores["FR"] += 1
    scores["TR"] += len(_TR_CHARS.findall(text)) * 2
    if _FR_CHARS.search(text) and scores["FR"]:
        scores["FR"] += 1
    best = max(scores, key=lambda key: scores[key])
    if scores[best] <= 0:
        return "unknown"
    # Turkish characters break a tie with English function words.
    if scores["TR"] == scores["EN"] and _TR_CHARS.search(text):
        return "TR"
    if scores["FR"] == scores["EN"] and scores["FR"] > scores["TR"] and _FR_CHARS.search(text):
        return "FR"
    return best
