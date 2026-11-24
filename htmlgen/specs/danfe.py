"""HTML do DANFE: XML -> modelo -> template Jinja (mesmas caixas, larguras em
mm e presets de ERP do renderizador `renderers/danfe`) -> PDF (Chromium)."""

from __future__ import annotations

import random
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from htmlgen.base import HtmlResult, HtmlSpec
from htmlgen.convert import barcode_svg_uri, logo_uri
from htmlgen.models.nfe import Fmt, parse_nfe
from htmlgen.render import HtmlRenderer, n_pages
from htmlgen.styles.danfe import Style, build_css, item_columns, sample_style, style_from_spec

_ENV = Environment(
    loader=FileSystemLoader(str(Path(__file__).resolve().parent.parent / "templates")),
    autoescape=True,
    undefined=StrictUndefined,
)


def parse_with_style(xml: str, style: Style) -> dict:
    return parse_nfe(xml, Fmt(qty_decimals=style.decimals, unit_decimals=style.decimals))


def _dup_rows(d: dict, style: Style) -> list[list[str]]:
    """Duplicatas em células de largura igual (como o DANFE real): N por linha,
    N = largura útil / maior texto. Células vazias de preenchimento = ''."""
    texts = [f"{x['n']}  {x['due']}  {x['value']}" for x in d["duplicatas"]]
    if not texts:
        return []
    mm_per_char = 7 * style.f * 0.3528 * 0.46
    page_w = 297 if style.landscape else 210
    edw = page_w - 2 * style.margin_mm - (19 if style.landscape else 0)
    per_line = max(1, int(edw / (max(len(t) for t in texts) * mm_per_char + 2)))
    rows = []
    for i in range(0, len(texts), per_line):
        line = texts[i : i + per_line]
        rows.append(line + [""] * (per_line - len(line)))
    return rows


def xml_to_html(
    xml: str,
    style: Style,
    seed: int = 0,
    page_label: str = "1/1",
    data: dict | None = None,
    fill_mm: float = 0.0,
) -> str:
    """HTML completo e autocontido (CSS inline, logo/barcode em data URI)."""
    rng = random.Random(seed)
    d = data or parse_with_style(xml, style)
    tpl = _ENV.get_template("danfe.html.j2")
    return tpl.render(
        d=d,
        style=style,
        css=build_css(style, fill_mm),
        cols=item_columns(style, d["simples"]),
        dup_rows=_dup_rows(d, style),
        fill_mm=fill_mm,
        logo_uri=logo_uri(d["emit"]["name"], style.logo_style, rng) if style.has_logo else None,
        barcode_uri=barcode_svg_uri(d["chave_raw"]),
        page_label=page_label,
    )




def render_html_pdf(renderer: HtmlRenderer, xml: str, style: Style, seed: int, data: dict):
    """HTML completo + PDF (Chromium). Páginas únicas ganham `fill_mm` para a
    tabela de itens preencher a folha (como no DANFE real)."""
    html = xml_to_html(xml, style, seed=seed, page_label="1/1", data=data)
    pdf = renderer.html_to_pdf(html)
    n = n_pages(pdf)
    if n > 1:  # 2ª passada só para escrever "FOLHA 1/N"
        html = xml_to_html(xml, style, seed=seed, page_label=f"1/{n}", data=data)
        return html, renderer.html_to_pdf(html), n
    page_w, page_h = (297, 210) if style.landscape else (210, 297)
    free = page_h - 2 * style.margin_mm - renderer.measure_mm(html, page_w, style.margin_mm) - 1.0
    while free >= 3:
        html2 = xml_to_html(xml, style, seed=seed, page_label="1/1", data=data, fill_mm=free)
        pdf2 = renderer.html_to_pdf(html2)
        if n_pages(pdf2) == 1:
            return html2, pdf2, 1
        free -= 4
    return html, pdf, 1


def render_danfe_html(xml: str, fv: dict, seed: int, renderer: HtmlRenderer, lib_pdf=None, need_pdf=True) -> HtmlResult:
    rng = random.Random(seed)
    spec = (fv or {}).get("_render")
    style = style_from_spec(spec, rng) if spec else sample_style(rng)
    data = parse_with_style(xml, style)
    html, pdf, n = render_html_pdf(renderer, xml, style, seed, data)
    return HtmlResult(html_full=html, pdf_bytes=pdf, n_pages=n, style=style.to_dict(), md_style=style.md_style)


SPEC = HtmlSpec(name="danfe", render=render_danfe_html)
