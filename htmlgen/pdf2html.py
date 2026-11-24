"""HTML semântico derivado da GEOMETRIA do PDF real (renderers/).

Usado nos tipos de layout de posição absoluta (DACTE, DAMDFE, DACCe) e em
DANFSe/Portal NF-e: em vez de reescrever à mão o desenho de cada um, lê-se do
PDF o texto (com posição, tamanho, negrito), as linhas/retângulos e as imagens:

1. **células** = regiões brancas fechadas pelas linhas desenhadas (flood fill
   numa grade de 0,5 mm) — o mesmo que "detecção de células de tabela";
2. cada linha de texto é atribuída à célula que a contém; o que fica fora de
   qualquer célula é texto livre;
3. células viram campos `dl > div > dt + dd` (rótulo pequeno/regular + valor
   maior/negrito), faixas negritas e largas viram `h2` (e abrem `section`),
   regiões com várias linhas viram pares rótulo/valor, `table` ou `p`;
4. o mesmo DOM carrega estilo inline com a posição absoluta (mm) de cada texto
   e um SVG `data-decor` com as linhas — renderizado no Chromium reproduz o PDF.
   O HTML limpo (convert.to_clean_html) descarta tudo isso.

O texto é idêntico ao do PDF por construção (`text_fidelity` ≈ 1,0).
"""

from __future__ import annotations

import base64
import math
import re
from html import escape

import cv2
import fitz
import numpy as np

from htmlgen.styles.danfe import FONT_STACKS

MM = 25.4 / 72.0  # pt -> mm
PX_PER_MM = 2.0  # resolução da grade de células
_NS = "http://www.w3.org/2000/svg"


# ----------------------------------------------------------------- extração


def _font_key(name: str) -> str:
    n = name.lower()
    if "courier" in n or "mono" in n:
        return "courier"
    if "times" in n or "serif" in n:
        return "times"
    return "helvetica"


def _lines(page) -> tuple[list[dict], list[dict]]:
    """(itens horizontais, itens rotacionados) de texto. Cada item é um trecho de
    texto com estilo único: trechos adjacentes com o mesmo estilo são unidos,
    mas rótulo regular + valor negrito na mesma linha ficam separados."""
    horiz, rotated = [], []
    for b in page.get_text("dict")["blocks"]:
        if b.get("type") != 0:
            continue
        for ln in b["lines"]:
            horizontal = abs(ln["dir"][0] - 1) < 0.02 and abs(ln["dir"][1]) < 0.02
            cur = None
            for s in ln["spans"]:
                if not s["text"].strip():
                    if cur is not None:
                        cur["text"] += s["text"]
                    continue
                style = (round(s["size"], 1), bool((s["flags"] & 16) or "bold" in s["font"].lower()),
                         _font_key(s["font"]), s.get("color", 0))
                bbox = [v * MM for v in s["bbox"]]
                if cur is not None and cur["style"] == style:
                    cur["text"] += s["text"]
                    cur["bbox"][2] = bbox[2]
                    continue
                if cur is not None:
                    (horiz if horizontal else rotated).append(cur)
                cur = {
                    "text": s["text"], "bbox": bbox, "size": s["size"], "bold": style[1], "font": style[2],
                    "origin": [v * MM for v in s["origin"]], "dir": ln["dir"], "color": style[3], "style": style,
                }
            if cur is not None:
                (horiz if horizontal else rotated).append(cur)
    for it in horiz + rotated:
        it["text"] = it["text"].strip()
    return [i for i in horiz if i["text"]], [i for i in rotated if i["text"]]


def _drawings(page):
    """(segmentos de borda, desenhos para o SVG, barras de código de barras)."""
    segs, shapes, bars = [], [], []
    for d in page.get_drawings():
        stroke, fill = d.get("color"), d.get("fill")
        width = (d.get("width") or 0.0) * MM
        for it in d["items"]:
            op = it[0]
            if op == "l":
                p1, p2 = it[1], it[2]
                if stroke is not None:
                    segs.append((p1.x * MM, p1.y * MM, p2.x * MM, p2.y * MM))
                shapes.append(("line", (p1.x * MM, p1.y * MM, p2.x * MM, p2.y * MM), d))
            elif op == "re":
                r = it[1]
                x0, y0, x1, y1 = r.x0 * MM, r.y0 * MM, r.x1 * MM, r.y1 * MM
                w, h = x1 - x0, y1 - y0
                if fill is not None and stroke is None and w < 1.3 and h > 4.0:
                    bars.append((x0, y0, x1, y1))
                if stroke is not None and not (fill is not None and (w < 0.6 or h < 0.6)):
                    segs += [(x0, y0, x1, y0), (x1, y0, x1, y1), (x1, y1, x0, y1), (x0, y1, x0, y0)]
                shapes.append(("rect", (x0, y0, x1, y1), d))
            elif op == "qu":
                q = it[1]
                shapes.append(("rect", (q.rect.x0 * MM, q.rect.y0 * MM, q.rect.x1 * MM, q.rect.y1 * MM), d))
    return segs, shapes, bars


def _cells(segs, w_mm, h_mm):
    """Rótulos de células por flood-fill da área não coberta por linhas."""
    W, H = int(w_mm * PX_PER_MM) + 2, int(h_mm * PX_PER_MM) + 2
    mask = np.zeros((H, W), np.uint8)
    for x0, y0, x1, y1 in segs:
        cv2.line(
            mask,
            (round(x0 * PX_PER_MM), round(y0 * PX_PER_MM)),
            (round(x1 * PX_PER_MM), round(y1 * PX_PER_MM)),
            255, 2,
        )
    free = (mask == 0).astype(np.uint8)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(free, connectivity=4)
    # fundo = componente do canto (0,0); lixo = componentes minúsculos
    bg = labels[0, 0]
    keep = {i for i in range(1, n) if i != bg and stats[i, cv2.CC_STAT_AREA] >= 12}
    return labels, stats, keep


def _cell_of(labels, keep, item) -> int | None:
    x0, y0, x1, y1 = item["bbox"]
    cx, cy = (x0 + x1) / 2 * PX_PER_MM, (y0 + y1) / 2 * PX_PER_MM
    ox, oy = item["origin"][0] * PX_PER_MM, item["origin"][1] * PX_PER_MM
    H, W = labels.shape
    for px, py in ((cx, cy), (ox + 1, oy - 2), (cx, cy - 2), (cx, cy + 2)):
        xi, yi = int(px), int(py)
        if 0 <= xi < W and 0 <= yi < H and labels[yi, xi] in keep:
            return int(labels[yi, xi])
    return None


# ----------------------------------------------------------------- montagem


def _text_lines(items):
    """Agrupa itens em linhas visuais pela LINHA DE BASE (tolerância 0,7 mm) —
    evita misturar colunas escalonadas (ex.: CEP e IE em alturas diferentes)."""
    lines = []
    for it in sorted(items, key=lambda i: (i["origin"][1], i["bbox"][0])):
        for ln in lines:
            if abs(ln["base"] - it["origin"][1]) <= 0.7:
                ln["items"].append(it)
                ln["y"] = (min(ln["y"][0], it["bbox"][1]), max(ln["y"][1], it["bbox"][3]))
                break
        else:
            lines.append({"base": it["origin"][1], "y": (it["bbox"][1], it["bbox"][3]), "items": [it]})
    for ln in lines:
        ln["items"].sort(key=lambda i: i["bbox"][0])
    return sorted(lines, key=lambda l: l["base"])


def _pairs(its):
    """Segmenta uma linha [rótulo, valor(es)negrito, rótulo, valor...] em pares.
    None se a linha não segue esse padrão (1º item regular e algum item em negrito)."""
    if not (len(its) >= 2 and not its[0]["bold"] and any(i["bold"] for i in its[1:])):
        return None
    out = []
    for it in its:
        if not it["bold"]:
            out.append([it, []])
        else:
            out[-1][1].append(it)
    return out


def _pair_divs(b, pairs) -> str:
    return "".join(
        f"<div><dt>{b.span(lab)}</dt><dd>{' '.join(b.span(v) for v in vals)}</dd></div>" for lab, vals in pairs
    )


_COLON = re.compile(r"^(?P<k>[^:]{2,45}):\s+(?P<v>\S.{0,200})$")


def _split_colon(b, it):
    """'Rótulo: valor' num único trecho -> par com dois spans (posição do valor
    estimada pela proporção de caracteres)."""
    m = _COLON.match(it["text"])
    if not m or it["text"].count(":") > 3:
        return None
    k, v = m.group("k") + ":", m.group("v")
    x0, y0, x1, y1 = it["bbox"]
    xs = x0 + (x1 - x0) * len(k) / max(len(it["text"]), 1)
    ki = {**it, "text": k, "bbox": [x0, y0, xs, y1]}
    vi = {**it, "text": v, "bbox": [xs, y0, x1, y1]}
    return f"<div><dt>{b.span(ki)}</dt><dd>{b.span(vi)}</dd></div>"


def _is_label(it, ref_size, any_bold_other) -> bool:
    return it["size"] < ref_size * 0.97 or (not it["bold"] and any_bold_other)


class _Builder:
    """Emite o DOM semântico + o estilo absoluto de cada texto."""

    def __init__(self, y_off: float, images_alt: list):
        self.y_off = y_off

    def span(self, it) -> str:
        x0, y0, x1, y1 = it["bbox"]
        style = (
            f"left:{x0:.2f}mm;top:{y0 + self.y_off:.2f}mm;font-size:{it['size']:.2f}pt;"
            f"line-height:{max(y1 - y0, 1):.2f}mm;font-family:{FONT_STACKS[it['font']]};"
            f"font-weight:{700 if it['bold'] else 400}"
        )
        col = it.get("color") or 0
        if col:
            style += f";color:#{col:06x}"
        return f'<span class="t" style="{style}">{escape(it["text"])}</span>'

    def lines_html(self, items) -> str:
        """Itens (uma ou mais linhas) -> spans com <br> entre linhas."""
        out = []
        for ln in _text_lines(items):
            out.append(" ".join(self.span(i) for i in ln["items"]))
        return "<br>".join(out)


def _is_title(it) -> bool:
    t = it["text"]
    return len(t) >= 8 and t == t.upper() and not any(ch.isdigit() for ch in t) and (it["bold"] or it["size"] >= 6)


def _row_groups(cells):
    cells = sorted(cells, key=lambda c: (c["y0"], c["x0"]))
    rows = []
    for c in cells:
        for r in rows:
            if min(r["y1"], c["y1"]) - max(r["y0"], c["y0"]) > 0.5 * min(r["y1"] - r["y0"], c["y1"] - c["y0"]):
                r["cells"].append(c)
                r["y0"], r["y1"] = min(r["y0"], c["y0"]), max(r["y1"], c["y1"])
                break
        else:
            rows.append({"y0": c["y0"], "y1": c["y1"], "cells": [c]})
    for r in rows:
        r["cells"].sort(key=lambda c: c["x0"])
    return sorted(rows, key=lambda r: r["y0"])


def _cell_html(b: _Builder, cell) -> str:
    """Uma célula -> `div` de campo, ou lista de pares/tabela/parágrafos para regiões grandes."""
    its = cell["items"]
    lines = _text_lines(its)
    if len(lines) <= 2 and len(its) <= 3:
        if len(lines) == 1 and len(its) == 1:
            # item único: papel (rótulo × valor) é ambíguo -> neutro, sem afirmar pareamento
            return f"<div><dd>{b.span(its[0])}</dd></div>"
        if len(lines) == 2 and len(lines[0]["items"]) == 1:
            l1, l2 = lines[0]["items"][0], lines[1]["items"]
            ref = max(i["size"] for i in l2)
            any_bold = any(i["bold"] for i in l2)
            if _is_label(l1, ref, any_bold) or (not l1["bold"] and any_bold):
                return f"<div><dt>{b.span(l1)}</dt><dd>{' '.join(b.span(i) for i in l2)}</dd></div>"
        if len(lines) == 1 and len(its) >= 2:
            pr = _pairs(lines[0]["items"])
            if pr:
                return _pair_divs(b, pr)
            first, rest = lines[0]["items"][0], lines[0]["items"][1:]
            if _is_label(first, max(i["size"] for i in rest), any(i["bold"] for i in rest)):
                return f"<div><dt>{b.span(first)}</dt><dd>{' '.join(b.span(i) for i in rest)}</dd></div>"
        return f"<div><dd>{b.lines_html(its)}</dd></div>"
    return _region_html(b, its)


def _region_html(b: _Builder, items) -> str:
    """Região com várias linhas: pares rótulo/valor, tabela ou parágrafo com <br>."""
    lines = _text_lines(items)

    def is_pair(ln):
        return _pairs(ln["items"]) is not None

    n_multi = sum(len(l["items"]) >= 2 for l in lines)
    parts = []
    if n_multi >= 3 and n_multi >= 0.6 * len(lines) and sum(map(is_pair, lines)) < 0.6 * len(lines):
        # tabela: 1ª linha é cabeçalho se tudo for rótulo (negrito/pequeno)
        head_like = all(i["bold"] or i["size"] <= 7 for i in lines[0]["items"])
        rows = []
        for idx, ln in enumerate(lines):
            tag = "th" if (idx == 0 and head_like) else "td"
            rows.append((tag, "".join(f"<{tag}>{b.span(i)}</{tag}>" for i in ln["items"])))
        thead = f"<thead><tr>{rows[0][1]}</tr></thead>" if head_like else ""
        body = "".join(f"<tr>{c}</tr>" for _t, c in (rows[1:] if head_like else rows))
        return f"<table>{thead}<tbody>{body}</tbody></table>"
    buf, pairs = [], []

    def flush_pairs():
        if pairs:
            parts.append("<dl>" + "".join(pairs) + "</dl>")
            pairs.clear()

    def flush_text():
        if buf:
            parts.append("<p>" + "<br>".join(buf) + "</p>")
            buf.clear()

    for ln in lines:
        if is_pair(ln):
            flush_text()
            pairs.append(_pair_divs(b, _pairs(ln["items"])))
            continue
        its_ = ln["items"]
        colon = _split_colon(b, its_[0]) if len(its_) == 1 else None
        if colon:
            flush_text()
            pairs.append(colon)
        elif len(its_) == 1 and _is_title(its_[0]) and len(lines) > 1:
            flush_pairs()
            flush_text()
            parts.append(f"<h3>{b.span(its_[0])}</h3>")
        else:
            flush_pairs()
            buf.append(" ".join(b.span(i) for i in its_))
    flush_pairs()
    flush_text()
    return "".join(parts)


def _svg(shapes, w_mm, h_mm) -> str:
    out = [f'<svg data-decor xmlns="{_NS}" class="vec" width="{w_mm:.1f}mm" height="{h_mm:.1f}mm" '
           f'viewBox="0 0 {w_mm:.1f} {h_mm:.1f}">']

    def rgb(c):
        return "none" if c is None else f"rgb({round(c[0] * 255)},{round(c[1] * 255)},{round(c[2] * 255)})"

    for kind, g, d in shapes:
        stroke, fill = d.get("color"), d.get("fill")
        sw = max((d.get("width") or 0.2) * MM, 0.05)
        dash = ""
        m = d.get("dashes") or ""
        nums = [float(t) for t in m.replace("[", " ").replace("]", " ").split()[:-1]] if "[" in m else []
        if nums and sum(nums) > 0:
            dash = f' stroke-dasharray="{" ".join(f"{n * MM:.2f}" for n in nums)}"'
        op = f' fill-opacity="{d["fill_opacity"]:.2f}"' if d.get("fill_opacity") not in (None, 1) else ""
        if kind == "line":
            if stroke is None:
                continue
            x0, y0, x1, y1 = g
            out.append(f'<line x1="{x0:.2f}" y1="{y0:.2f}" x2="{x1:.2f}" y2="{y1:.2f}" stroke="{rgb(stroke)}" '
                       f'stroke-width="{sw:.2f}"{dash}/>')
        else:
            x0, y0, x1, y1 = g
            out.append(f'<rect x="{x0:.2f}" y="{y0:.2f}" width="{x1 - x0:.2f}" height="{y1 - y0:.2f}" '
                       f'fill="{rgb(fill)}"{op} stroke="{rgb(stroke)}" stroke-width="{sw:.2f}"{dash}/>')
    out.append("</svg>")
    return "".join(out)


def pdf_to_html(pdf_bytes: bytes, title: str = "Documento", watermark_label: str = "Marca d'água") -> str:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    w_mm, h_mm = doc[0].rect.width * MM, doc[0].rect.height * MM
    body, svgs, extras = [], [], []

    for pno, page in enumerate(doc):
        y_off = pno * h_mm
        b = _Builder(y_off, [])
        horiz, rotated = _lines(page)
        segs, shapes, bars = _drawings(page)
        labels, stats, keep = _cells(segs, w_mm, h_mm)

        cells: dict[int, dict] = {}
        free = []
        for it in horiz:
            cid = _cell_of(labels, keep, it)
            if cid is None:
                free.append(it)
            else:
                c = cells.setdefault(cid, {"items": []})
                c["items"].append(it)
        for cid, c in cells.items():
            x, y, w, h = (stats[cid, k] / PX_PER_MM for k in (cv2.CC_STAT_LEFT, cv2.CC_STAT_TOP,
                                                           cv2.CC_STAT_WIDTH, cv2.CC_STAT_HEIGHT))
            c.update(x0=x, y0=y, x1=x + w, y1=y + h, w=w, h=h)

        # fluxo de blocos: linhas de células, texto livre e imagens, em ordem vertical
        flow = []
        for r in _row_groups(list(cells.values())):
            flow.append((r["y0"], 0, "row", r))
        for ln in _text_lines(free):
            flow.append((ln["y"][0], 1, "free", ln))
        for info in page.get_image_info(xrefs=True):
            x0, y0, x1, y1 = (v * MM for v in info["bbox"])
            try:
                img = doc.extract_image(info["xref"])
                uri = f"data:image/{img['ext']};base64,{base64.b64encode(img['image']).decode()}"
            except Exception:  # noqa: BLE001 - imagem sem xref extraível: só marca a posição
                uri = ""
            alt = "Logotipo" if x0 < 55.0 else "QR Code"
            flow.append((y0, 2, "img", (x0, y0, x1, y1, uri, alt)))
        if bars:
            bx0, by0 = min(r[0] for r in bars), min(r[1] for r in bars)
            bx1, by1 = max(r[2] for r in bars), max(r[3] for r in bars)
            flow.append((by0, 2, "img", (bx0, by0, bx1, by1, "", "Código de barras")))
        flow.sort(key=lambda t: (t[0], t[1]))

        sections, cur = [], {"h2": None, "parts": []}

        def new_section(h2=None):
            nonlocal cur
            if cur["h2"] or cur["parts"]:
                sections.append(cur)
            cur = {"h2": h2, "parts": []}

        for _y, _k, kind, obj in flow:
            if kind == "row":
                cs = obj["cells"]
                # faixa de título: 1 célula, 1 item, negrito, baixa e larga
                if (len(cs) == 1 and len(cs[0]["items"]) == 1 and _is_title(cs[0]["items"][0])
                        and cs[0]["h"] <= 4.8 and cs[0]["w"] >= 0.4 * w_mm):
                    new_section(f"<h2>{b.span(cs[0]['items'][0])}</h2>")
                    continue
                pend = []

                def flush_pend():
                    if pend:
                        cur["parts"].append("<dl>" + "".join(pend) + "</dl>")
                        pend.clear()

                for c in cs:
                    html_c = _cell_html(b, c)
                    if html_c.startswith("<div>"):
                        pend.append(html_c)
                    else:
                        flush_pend()
                        cur["parts"].append(html_c)
                flush_pend()
            elif kind == "free":
                cur["parts"].append("<p>" + " ".join(b.span(i) for i in obj["items"]) + "</p>")
            else:
                x0, y0, x1, y1, uri, alt = obj
                style = (f"left:{x0:.2f}mm;top:{y0 + y_off:.2f}mm;width:{x1 - x0:.2f}mm;height:{y1 - y0:.2f}mm;"
                         + ("" if uri else "visibility:hidden"))
                src = f' src="{uri}"' if uri else ""
                cur["parts"].append(f'<img class="im" style="{style}"{src} alt="{alt}">')
        new_section()
        for s in sections:
            body.append("<section>" + (s["h2"] or "") + "".join(s["parts"]) + "</section>")
        svgs.append(f'<div data-decor class="pg" style="top:{y_off:.2f}mm">{_svg(shapes, w_mm, h_mm)}</div>')

        for it in rotated:  # marca d'água etc.: texto rotacionado
            ang = math.degrees(math.atan2(it["dir"][1], it["dir"][0]))
            ox, oy = it["origin"]
            style = (f"left:{ox:.2f}mm;top:{oy + y_off - it['size'] * MM:.2f}mm;font-size:{it['size']:.2f}pt;"
                     f"font-weight:{700 if it['bold'] else 400};font-family:{FONT_STACKS[it['font']]};"
                     f"color:#{(it['color'] or 0):06x};transform-origin:0 100%;transform:rotate({ang:.1f}deg)")
            extras.append(f'<aside data-kind="watermark"><p><span class="t" style="{style}">{escape(it["text"])}</span></p></aside>')

    n = len(doc)
    css = f"""
@page {{ size: {w_mm:.1f}mm {h_mm:.1f}mm; margin: 0; }}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
html, body {{ background: #fff; }}
article {{ position: relative; width: {w_mm:.1f}mm; height: {n * h_mm:.1f}mm; overflow: hidden; }}
.t {{ position: absolute; white-space: pre; color: #000; }}
.pg {{ position: absolute; left: 0; width: {w_mm:.1f}mm; height: {h_mm:.1f}mm; }}
.vec {{ position: absolute; left: 0; top: 0; }}
.im {{ position: absolute; object-fit: contain; }}
table {{ border-collapse: collapse; }}
"""
    return (
        f'<!DOCTYPE html>\n<html lang="pt-BR"><head><meta charset="utf-8"><title>{escape(title)}</title>'
        f"<style>{css}</style></head><body><article>{''.join(svgs)}{''.join(body)}{''.join(extras)}</article></body></html>"
    )
