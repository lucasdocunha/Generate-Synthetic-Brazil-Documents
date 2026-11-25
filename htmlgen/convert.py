"""Conversões genéricas (independentes do tipo de documento):
helpers de data-URI (barcode/logo), HTML completo -> HTML limpo -> Markdown.

Contrato do HTML (todo template de `htmlgen/templates/` deve segui-lo):
- um `<article>` cujos filhos de topo são os blocos na ordem de leitura;
- campos como `dl > div > dt + dd`; tabelas com `thead/tbody`;
- cada valor num único trecho de texto (a oclusão casa por texto);
- decoração sem conteúdo (hr, colgroup, linhas de preenchimento) marcada com
  `data-decor`: some do HTML limpo e do Markdown.
O HTML limpo é derivado do completo (remove só a camada de estilo) e o
Markdown, da árvore DOM — os três nunca divergem no conteúdo.
"""

from __future__ import annotations

import base64
import random
import re
from io import BytesIO

import barcode
import lxml.html
from barcode.writer import SVGWriter
from lxml import etree

from generator.branding.logo_factory import generate_company_logo


def _data_uri(data: bytes, mime: str) -> str:
    return f"data:{mime};base64,{base64.b64encode(data).decode()}"


def barcode_svg_uri(chave: str) -> str | None:
    """Code128 da chave de acesso (sintética — a chave do gerador não é
    de nenhuma NF-e real, e o barcode só reproduz o aspecto visual)."""
    digits = re.sub(r"\D", "", chave)
    if not digits:
        return None
    buf = BytesIO()
    barcode.get("code128", digits, writer=SVGWriter()).write(
        buf, options={"write_text": False, "module_height": 8.0, "quiet_zone": 1.0, "module_width": 0.25}
    )
    return _data_uri(buf.getvalue(), "image/svg+xml")


def png_data_uri(data: bytes) -> str:
    return _data_uri(data, "image/png")


def logo_uri(name: str, logo_style: str | None, rng: random.Random) -> str:
    data = generate_company_logo(rng, name, style=logo_style).getvalue()
    return _data_uri(data, "image/png")



# ------------------------------------------------------------------ clean html

def _simplify(doc):
    """Reduz o DOM à ESTRUTURA: article > section/header/h*/dl(dt,dd)/table/p/img.

    Sem head/doctype, sem atributos, sem div/span/b/small/br. Imagens (logo, QR,
    barcode) e objetos sobrepostos (<aside>: carimbo, POS, assinatura, marca
    d'água) viram `<img>` vazio — só a sinalização de que há uma imagem ali."""
    for el in doc.xpath("//style | //script | //*[@data-decor]"):
        el.getparent().remove(el)
    for el in doc.xpath("//aside"):
        img = lxml.html.Element("img")
        img.tail = el.tail
        el.getparent().replace(el, img)
    for br in doc.xpath("//br"):
        br.tail = " " + (br.tail or "")
        br.drop_tag()
    for el in doc.xpath("//span | //b | //small | //div | //strong | //i"):
        el.drop_tag()
    for el in doc.iter():
        if isinstance(el.tag, str):
            el.attrib.clear()
    article = doc.find(".//article")
    root = article if article is not None else doc.find("body")
    for el in root.iter():
        if not isinstance(el.tag, str):
            continue
        if el.text is not None:
            el.text = " ".join(el.text.split()) or None
        if el.tail is not None:
            el.tail = " ".join(el.tail.split()) or None
    for p in root.xpath(".//p[not(normalize-space()) and not(.//img)]"):
        p.getparent().remove(p)
    return root


def to_clean_html(full_html: str) -> str:
    """HTML-alvo só com estrutura (ver `_simplify`)."""
    root = _simplify(lxml.html.document_fromstring(full_html))
    etree.indent(root, space="  ")
    return etree.tostring(root, encoding="unicode", method="html").rstrip() + "\n"


# -------------------------------------------------------------------- markdown


def _inline(el) -> str:
    parts = [el.text or ""]
    for ch in el:
        tag = ch.tag if isinstance(ch.tag, str) else ""
        if tag == "br":
            parts.append("<br>")
        elif tag == "b":
            sep = " " if "".join(parts) and not "".join(parts).endswith(" ") else ""
            parts.append(f"{sep}**{_inline(ch).strip()}**")
        elif tag == "img":
            parts.append("![]()")
        else:
            parts.append(_inline(ch))
        parts.append(ch.tail or "")
    return re.sub(r"[ \t\n]+", " ", "".join(parts)).strip()


def _cell(td) -> str:
    """Conteúdo de célula de tabela (<br> das linhas extras do item preservado)."""
    return _inline(td).replace("|", "\\|")


def _table_md(rows: list[list[str]], header: list[str], aligns: list[str]) -> str:
    sep = [{"r": "---:", "c": ":---:"}.get(a, "---") for a in aligns]
    lines = ["| " + " | ".join(header) + " |", "| " + " | ".join(sep) + " |"]
    lines += ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join(lines)


def _collect_fields(dl_list) -> list[tuple[str, str]]:
    """Pares (dt, dd): dt e dd são irmãos; dd/dt isolados viram par com o outro vazio."""
    out = []
    for dl in dl_list:
        pending = None
        for ch in dl:
            if ch.tag == "dt":
                if pending is not None:
                    out.append((pending, ""))
                pending = _inline(ch)
            elif ch.tag == "dd":
                out.append((pending or "", _inline(ch)))
                pending = None
        if pending is not None:
            out.append((pending, ""))
    return out


def _walk(el, md_style: str, out: list[str]):
    pending_dls: list = []

    def flush():
        if not pending_dls:
            return
        fields = _collect_fields(pending_dls)
        pending_dls.clear()
        if not fields:
            return
        if md_style == "bullets":
            out.append("\n".join((f"- **{k}:** {v}" if k else f"- {v}").rstrip() for k, v in fields))
        else:
            out.append(
                _table_md([[k, v.replace("|", "\\|")] for k, v in fields], ["Campo", "Valor"], ["", ""])
            )

    for ch in el:
        tag = ch.tag if isinstance(ch.tag, str) else ""
        if tag == "dl":
            pending_dls.append(ch)
            continue
        flush()
        if tag in ("h1", "h2", "h3"):
            out.append("#" * int(tag[1]) + " " + _inline(ch))
        elif tag == "p":
            out.append(_inline(ch))
        elif tag == "img":
            out.append("![]()")
        elif tag == "table" and not ch.findall("./thead/tr/th"):
            cells = [_inline(td) for td in ch.iter("td")]
            out.append("\n".join(f"- {c}" for c in cells if c))
        elif tag == "table":
            ths = ch.findall("./thead/tr/th")
            header = [_inline(t) for t in ths]
            aligns = ["" for _ in ths]
            rows = [[_cell(td) for td in tr.findall("td")] for tr in ch.findall("./tbody/tr")]
            out.append(_table_md(rows, header, aligns))
        elif tag in ("section", "header", "article"):
            _walk(ch, md_style, out)
    flush()


def to_markdown(html: str, md_style: str = "table") -> str:
    """Markdown GFM derivado da estrutura simplificada (aceita HTML completo ou limpo)."""
    root = _simplify(lxml.html.document_fromstring(html))
    out: list[str] = []
    _walk(root, md_style, out)
    return "\n\n".join(x for x in out if x.strip()) + "\n"
