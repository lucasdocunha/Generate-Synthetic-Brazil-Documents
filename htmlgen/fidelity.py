"""Métrica de consistência HTML <-> imagem: fração dos tokens do HTML limpo
presentes no texto do PDF que gerou a imagem (1.0 = nada cortado/oculto)."""

from __future__ import annotations

import re
import unicodedata
from collections import Counter

import fitz
import lxml.html


def tokens(text: str) -> Counter:
    text = unicodedata.normalize("NFKC", text).casefold()
    return Counter(re.findall(r"\w+", text, flags=re.UNICODE))


def text_fidelity(clean_html: str, pdf_bytes: bytes) -> float:
    html_text = " ".join(lxml.html.document_fromstring(clean_html).body.itertext())
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pdf_text = "\n".join(p.get_text("text") for p in doc)
    doc.close()
    h, p = tokens(html_text), tokens(pdf_text)
    total = sum(h.values())
    return round(sum((h & p).values()) / total, 4) if total else 0.0
