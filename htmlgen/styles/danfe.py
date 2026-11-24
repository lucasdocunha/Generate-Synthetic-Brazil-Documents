"""Estilo do DANFE em HTML: reproduz a estrutura real do DANFE (mesmas caixas,
larguras em mm, tamanhos de fonte e estilos de tabela do renderizador
`renderers`) e varia pelos mesmos presets de ERP que o gerador já
sorteia (`field_values["_render"]`).

Dois jeitos de obter um `Style`:
- `style_from_spec(spec)`: a partir do `_render` do gerador — o HTML fica com
  o mesmo layout do "gêmeo" em PDF;
- `sample_style(rng)`: sorteio independente (HTML a partir de qualquer XML).
"""

from __future__ import annotations

import random
from dataclasses import asdict, dataclass

FONT_STACKS = {
    "times": "'Liberation Serif', 'Times New Roman', Times, serif",
    "helvetica": "'Liberation Sans', Arial, Helvetica, sans-serif",
    "courier": "'Liberation Mono', 'Courier New', Courier, monospace",
}

# Larguras (mm) das colunas da tabela de itens; None = coluna flexível
# (descrição) ou CST (6mm / 8mm no Simples). Idênticas às de
# `Danfe._product_col_widths`.
COL_WIDTHS_SMALL = (15, None, 11, "cst", 7, 6, 12, 13, 13, 13, 10, 10, 9, 8)
COL_WIDTHS_BIG = (15, None, 14, 8, 8, 8, 12, 13, 15, 14, 13, 10, 9, 9)

COL_KEYS = ["code", "desc", "ncm", "cst", "cfop", "un", "qty", "unit", "total",
            "bc", "icms", "ipi", "p_icms", "p_ipi"]

COL_LABELS = {
    "standard": ["CÓDIGO", "DESCRIÇÃO DOS PRODUTOS / SERVIÇOS", "NCM/SH", "{cst}", "CFOP", "UN.",
                 "QTD.", "V.UNIT.", "V.TOTAL", "BC.ICMS", "V.ICMS", "V.IPI", "%ICMS", "%IPI"],
    "fuel_anp": ["CÓD. PROD.", "DESCRIÇÃO DO PRODUTO/SERVIÇO", "CÓD. NCM", "{cst}", "CFOP", "UND",
                 "QUANTIDADE", "V. UNITÁRIO", "V. TOTAL", "BC ICMS", "V. ICMS", "V. IPI",
                 "ALIQ. ICMS", "ALIQ. IPI"],
    "discount_liquid": ["CÓDIGO", "DESCRIÇÃO DO PRODUTO / SERVIÇO", "NCM/SH", "{cst}", "CFOP", "UNID.",
                        "QTDE.", "VALOR UNIT.", "VALOR LÍQ.", "B. CÁLC. ICMS", "VALOR ICMS",
                        "VALOR IPI", "ALIQ. ICMS", "ALIQ. IPI"],
}

_ERPS = ["standard", "linx_autosystem", "xpert", "galago", "minimal_open", "classic_landscape"]


@dataclass
class Style:
    font_type: str = "times"  # times | helvetica | courier
    big: bool = False  # FontSize.BIG (x1.35 no conteúdo)
    receipt_pos: str = "top"  # top | bottom | left (paisagem)
    landscape: bool = False
    product_table_style: str = "full_frame"  # full_frame | full_vertical_grid | open_bottom
    product_columns_preset: str = "standard"  # standard | fuel_anp | discount_liquid
    has_logo: bool = True
    logo_style: str | None = None
    display_pis_cofins: bool = False
    invoice_display: str = "full"  # full | duplicates_only
    decimals: int = 4
    sub_emit_credit: str = ""
    mid_page_credit: str = ""
    footer_left_text: str = ""
    footer_right_text: str = ""
    erp_style: str = "standard"
    margin_mm: float = 5.0
    md_style: str = "table"  # formato do Markdown alvo: table | bullets

    @property
    def f(self) -> float:
        return 1.35 if self.big else 1.0

    def to_dict(self) -> dict:
        return asdict(self)


def style_from_spec(spec: dict, rng: random.Random) -> Style:
    """`field_values["_render"]` -> Style (mesmo layout do PDF gêmeo)."""
    erp = spec.get("erp_style", "standard")
    logo_style = {"galago": "badge_seal", "linx_autosystem": "fuel_shield", "xpert": "fuel_shield"}.get(erp)
    landscape = bool(spec.get("landscape"))
    return Style(
        font_type=spec.get("font_type", "Times").lower(),
        big=spec.get("font_size") == "BIG",
        receipt_pos="left" if landscape else spec.get("receipt_pos", "top"),
        landscape=landscape,
        product_table_style=spec.get("product_table_style", "full_frame"),
        product_columns_preset=spec.get("product_columns_preset", "standard"),
        has_logo=bool(spec.get("has_logo")),
        logo_style=logo_style or rng.choice(["badge_seal", "modern_corporate", "fuel_shield", "minimal_monogram"]),
        display_pis_cofins=bool(spec.get("display_pis_cofins")),
        invoice_display=spec.get("invoice_display", "full"),
        decimals=int(spec.get("decimals", 4)),
        sub_emit_credit=spec.get("sub_emit_credit", ""),
        mid_page_credit=spec.get("mid_page_credit", ""),
        footer_left_text=spec.get("footer_left_text", ""),
        footer_right_text=spec.get("footer_right_text", ""),
        erp_style=erp,
        margin_mm=rng.choices([5.0, 4.0, 7.0, 10.0], weights=[80, 8, 8, 4])[0],
        md_style=rng.choice(["table", "bullets"]),
    )


def sample_style(rng: random.Random) -> Style:
    """Sorteio independente, com as mesmas famílias de ERP do gerador."""
    erp = rng.choices(_ERPS, weights=[40, 14, 14, 10, 12, 10])[0]
    landscape = erp == "classic_landscape"
    font = rng.choices(["times", "helvetica", "courier"], weights=[60, 28, 12])[0]
    spec = {
        "erp_style": erp,
        "font_type": font.capitalize(),
        "font_size": "BIG" if rng.random() < 0.2 else "SMALL",
        "landscape": landscape,
        "receipt_pos": "bottom" if rng.random() < 0.25 else "top",
        "product_table_style": (
            "open_bottom" if erp == "minimal_open"
            else "full_frame" if erp == "standard" else "full_vertical_grid"
        ),
        "product_columns_preset": {"linx_autosystem": "fuel_anp", "xpert": "discount_liquid"}.get(erp, "standard"),
        "has_logo": rng.random() < 0.7,
        "display_pis_cofins": rng.random() < 0.15,
        "invoice_display": "duplicates_only" if rng.random() < 0.3 else "full",
        "decimals": rng.choice([2, 3, 4, 4]),
    }
    if erp == "linx_autosystem":
        spec["footer_left_text"] = "LINX SISTEMAS E CONSULTORIA LTDA - AutoSystem 3.2.5.12 - www.linx.invalid"
    elif erp == "xpert":
        spec["sub_emit_credit"] = "xpert v3.5 - xpert.invalid"
        spec["footer_left_text"] = "(c)1993-2025 xpert v3.5 - xpert.invalid"
    elif erp == "galago":
        spec["mid_page_credit"] = "Implante esta NF-e na sua empresa: www.galago.invalid"
    return style_from_spec(spec, rng)


def item_columns(style: Style, simples: bool) -> list[dict]:
    """Colunas da tabela de itens: chave, rótulo, largura (mm; None=flex), alinhamento."""
    cst_label = "CSOSN" if simples else "CST"
    cst_w = 8 if simples else 6
    widths = COL_WIDTHS_BIG if style.big else COL_WIDTHS_SMALL
    labels = COL_LABELS[style.product_columns_preset]
    cols = []
    for i, key in enumerate(COL_KEYS):
        w = widths[i]
        if w == "cst":
            w = cst_w
        cols.append({
            "key": key,
            "label": labels[i].format(cst=cst_label),
            "w": w,
            "align": "r" if i >= 6 else "",
        })
    return cols


def build_css(s: Style, fill_mm: float = 0.0) -> str:
    f = s.f
    stack = FONT_STACKS.get(s.font_type, FONT_STACKS["times"])
    page = "297mm 210mm" if s.landscape else "210mm 297mm"
    lw = "0.2mm solid #000"
    content = 7 * f
    prod = 6 * f
    recv = 5 * f

    css = f"""
@page {{ size: {page}; margin: {s.margin_mm}mm; }}
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; padding: 0; background: #fff; }}
body {{ font-family: {stack}; font-size: {content}pt; line-height: 3mm; color: #000; }}
article {{ width: 100%; {'padding-left: 19mm; position: relative;' if s.receipt_pos == 'left' else ''} }}
section {{ margin: 0; padding: 0; }}
section > h2 {{ margin: 0; font-size: 6pt; font-weight: 700; line-height: 3mm; height: 3mm; text-transform: uppercase; }}
dl, dd, dt, p {{ margin: 0; padding: 0; }}
.row {{ display: flex; border-top: {lw}; border-left: {lw}; }}
.row + .row {{ border-top: 0; }}
.f {{ display: flex; flex-direction: column; min-height: 6mm; padding: 0 1mm; border-right: {lw}; border-bottom: {lw};
  flex: 1 1 0; min-width: 0; overflow: hidden; }}
.f[style] {{ flex: 0 0 auto; }}
.f dt {{ font-size: 5pt; line-height: 2.8mm; white-space: nowrap; overflow: hidden; }}
.f dd {{ font-size: {content}pt; line-height: 3mm; overflow-wrap: anywhere; white-space: pre-line; }}
.f.r dd {{ text-align: right; }}
.f.b dd {{ font-weight: 700; text-align: center; }}
.f.h20 {{ min-height: 20mm; }}
.receipt {{ display: flex; border: {lw}; height: 17mm; font-size: {recv}pt; }}
.receipt .r-main {{ flex: 1; display: flex; flex-direction: column; border-right: {lw}; min-width: 0; }}
.receipt .r-main > p {{ height: 8.5mm; padding: 1mm 1mm 0 1mm; font-size: {recv}pt; line-height: 2.8mm; border-bottom: {lw}; overflow: hidden; }}
.receipt .r-sign {{ display: flex; flex: 1; }}
.receipt .r-sign .f {{ border: 0; min-height: 0; padding-top: 0.5mm; }}
.receipt .r-sign .f:first-child {{ flex: 0 0 40mm; border-right: {lw}; }}
.receipt .r-sign dt {{ font-size: {recv}pt; }}
.receipt .r-num {{ flex: 0 0 30mm; text-align: center; font-weight: 700; font-size: 10pt; padding-top: 0.5mm; line-height: 4.4mm; }}
hr.dash {{ border: 0; border-top: 0.2mm dashed #000; margin: 1mm 0; }}
"""
    if s.receipt_pos == "left":
        css += f"""
.receipt.left {{ position: absolute; left: 0; top: 0; width: 19mm; height: {210 - 2 * s.margin_mm}mm; display: block; padding: 1mm; }}
.receipt.left > div {{ writing-mode: vertical-rl; transform: rotate(180deg); }}
"""
    css += f"""
header {{ display: grid; grid-template-columns: 1fr 33mm 88mm; height: 31mm; border: {lw}; }}
header > div {{ min-width: 0; overflow: hidden; }}
header > div + div {{ border-left: {lw}; }}
.emit {{ position: relative; text-align: center; }}
.emit h1 {{ margin: 1mm 0 0 0; font-size: 12pt; font-weight: 700; line-height: 4.4mm; height: 9mm; overflow: hidden; }}
.emit .addr {{ position: absolute; left: 0; right: 0; top: 12mm; font-size: 8pt; line-height: 3mm; padding: 0 1mm; }}
.emit img {{ position: absolute; left: 2mm; top: 10mm; width: 30mm; height: 20mm; object-fit: contain; }}
.emit.has-logo .addr {{ left: 32mm; padding: 0; }}
.ident h2 {{ margin: 0; text-align: center; font-size: 12pt; line-height: 4mm; font-weight: 700; }}
.ident .sub {{ text-align: center; font-size: 7pt; line-height: 2.6mm; }}
.ident .io {{ position: relative; margin: 0.5mm 0 0 1mm; font-size: 8pt; line-height: 3mm; }}
.ident .io b {{ position: absolute; right: 3mm; top: 0; width: 5mm; height: 5mm; border: {lw}; text-align: center;
  font-size: 10pt; line-height: 4mm; }}
.ident .num {{ margin: 0.5mm 0 0 1mm; font-size: 10pt; font-weight: 700; line-height: 4.5mm; }}
.ident .sf {{ margin-left: 1mm; font-size: 8pt; font-weight: 700; line-height: 3mm; }}
.code {{ display: flex; flex-direction: column; }}
.code .bars {{ height: 10mm; padding: 0.5mm; border-bottom: {lw}; }}
.code .bars img {{ width: 100%; height: 8.5mm; object-fit: fill; display: block; }}
.code dl .f {{ border: 0; border-bottom: {lw}; min-height: 6mm; }}
.code .verify {{ flex: 1; font-size: 10pt; line-height: 4.2mm; text-align: center; padding: 2.5mm 0.5mm 0 0.5mm; }}
table {{ width: 100%; border-collapse: collapse; table-layout: fixed; font-size: {prod}pt; }}
th {{ font-size: 5pt; font-weight: 700; text-align: left; vertical-align: top; line-height: 3mm; padding: 0 1mm; border: {lw}; }}
td {{ vertical-align: top; line-height: 3mm; padding: 0 1mm; border: {lw}; overflow-wrap: anywhere; }}
td.r {{ text-align: right; }}
thead {{ display: table-header-group; }} tr {{ break-inside: avoid; }}
table.dups td {{ font-size: {7 * f:.2f}pt; height: 3mm; }}
td.fill {{ height: {max(fill_mm, 0):.2f}mm; padding: 0; }}
.credit {{ text-align: center; font-weight: 700; font-size: 6pt; line-height: 3mm; }}
footer {{ display: flex; justify-content: space-between; margin-top: 1mm; line-height: 5mm; }}
footer .l {{ font-size: 6.5pt; }} footer .rt {{ font-size: 7pt; font-weight: 700; }}
"""
    if s.product_table_style == "full_frame":
        css += "td.fill.nov { border-left: 0; border-right: 0; border-top: 0; }\n"
    if s.product_table_style == "open_bottom":
        css += "td.fill { border: 0; }\n"
    return css
