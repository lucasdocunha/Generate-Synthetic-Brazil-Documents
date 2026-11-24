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

_KEEP_ATTRS = {"alt", "lang", "colspan", "rowspan", "charset", "data-kind", "data-subtype"}


def to_clean_html(full_html: str) -> str:
    """Remove a camada de estilo, preservando só semântica + texto.

    - tira <style>, class, style, id e src (imagens viram só `alt`);
    - achata <span>/<b> sem significado estrutural.
    """
    doc = lxml.html.document_fromstring(full_html)
    for el in doc.xpath("//style | //*[@data-decor]"):
        el.getparent().remove(el)
    for el in doc.iter():
        if not isinstance(el.tag, str):
            continue
        for a in list(el.attrib):
            if a not in _KEEP_ATTRS:
                del el.attrib[a]
    for el in doc.xpath("//span"):
        el.drop_tag()
    for el in doc.iter():
        if isinstance(el.tag, str):
            if el.text is not None and not el.text.strip():
                el.text = None
            if el.tail is not None and not el.tail.strip():
                el.tail = None
    etree.indent(doc, space="  ")
    return "<!DOCTYPE html>\n" + etree.tostring(doc, encoding="unicode", method="html")


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
            parts.append(f"![{ch.get('alt', '')}]()")
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
    out = []
    for dl in dl_list:
        for f in dl:
            dt, dd = f.find("dt"), f.find("dd")
            if dt is not None or dd is not None:
                out.append((_inline(dt) if dt is not None else "", _inline(dd) if dd is not None else ""))
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
            out.append(f"![{ch.get('alt', '')}]()")
        elif tag == "table" and not ch.findall("./thead/tr/th"):
            cells = [_inline(td) for td in ch.iter("td")]
            out.append("\n".join(f"- {c}" for c in cells if c))
        elif tag == "table":
            ths = ch.findall("./thead/tr/th")
            header = [_inline(t) for t in ths]
            aligns = [("r" if "r" in (t.get("class") or "").split() else "") for t in ths]
            rows = [[_cell(td) for td in tr.findall("td")] for tr in ch.findall("./tbody/tr")]
            out.append(_table_md(rows, header, aligns))
        elif tag == "aside":
            from htmlgen.occlusion import KIND_TITLE

            title = KIND_TITLE.get(ch.get("data-kind", ""), "Elemento")
            sub = f" ({ch.get('data-subtype')})" if ch.get("data-subtype") else ""
            body = [_inline(p) for p in ch.findall("p")]
            out.append("\n".join([f"> **{title}{sub}**"] + [f"> {b}" for b in body]))
        elif tag in ("div", "section", "header", "article"):
            _walk(ch, md_style, out)
    flush()


def to_markdown(html: str, md_style: str = "table") -> str:
    """Markdown GFM derivado da árvore do HTML. Recebe o HTML COMPLETO (as
    classes r/c só servem para alinhar colunas numéricas; o texto é idêntico
    ao do HTML limpo)."""
    doc = lxml.html.document_fromstring(html)
    body = doc.find("body")
    out: list[str] = []
    _walk(body, md_style, out)
    return "\n\n".join(x for x in out if x.strip()) + "\n"
