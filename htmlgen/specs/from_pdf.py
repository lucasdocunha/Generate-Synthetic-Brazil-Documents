"""Spec de HTML derivada do PDF real (ver htmlgen/pdf2html.py): DACTE, DAMDFE,
DACCe, DANFSe e Portal NF-e."""

from __future__ import annotations

import random

from htmlgen.base import HtmlResult, HtmlSpec
from htmlgen.pdf2html import pdf_to_html
from htmlgen.render import n_pages

TITLES = {
    "dacte": "DACTE", "damdfe": "DAMDFE", "dacce": "DACCe", "danfse": "DANFSe", "nfe_portal": "Consulta NF-e",
    "nfse_legado": "NFS-e",
}


def make_spec(name: str) -> HtmlSpec:
    def render(xml, fv, seed, renderer, lib_pdf=None, need_pdf=True) -> HtmlResult:
        if lib_pdf is None:
            raise ValueError(f"spec '{name}' deriva o HTML do PDF real: passe lib_pdf")
        html = pdf_to_html(lib_pdf, title=TITLES.get(name, name.upper()))
        pdf = renderer.html_to_pdf(html) if need_pdf else b""
        return HtmlResult(
            html_full=html, pdf_bytes=pdf, n_pages=n_pages(lib_pdf),
            style={"derived_from": "pdf_geometry"},
            md_style=random.Random(seed).choice(["table", "bullets"]),
        )

    return HtmlSpec(name=name, render=render)
