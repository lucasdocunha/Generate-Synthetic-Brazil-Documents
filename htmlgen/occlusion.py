"""Degradações no alvo HTML: carimbos, assinaturas e comprovantes POS.

Camadas do alvo (ver README):
- `html_clean` : o DOCUMENTO (tudo que o XML diz). Par da imagem limpa.
- `html_visible`: o que a imagem DEGRADADA mostra. Par de `images_aug/`:
    * cada artefato vira um `<img>` vazio (sinalização), inserido
      depois do bloco do documento que está logo acima dele na página;
    * campo coberto por um artefato vira `[ilegível]` (o modelo não deve
      "adivinhar" o que não se enxerga); campos só parcialmente cobertos ficam.

A cobertura vem das bboxes já reprojetadas do `label` (augmentation/).
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter

import lxml.html

ARTIFACT_TYPES = {"stamp", "pos_receipt", "signature"}
KIND_TITLE = {
    "pos_receipt": "Comprovante de cartão (POS)", "stamp": "Carimbo", "signature": "Assinatura",
    "watermark": "Marca d'água",
}
ILLEGIBLE = "[ilegível]"
_TEXT_TAGS = ".//dd | .//dt | .//td | .//th | .//p | .//h1 | .//h2"


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", s).casefold()
    return re.sub(r"[^\w]", "", s, flags=re.UNICODE)


def _covered_ratio(bbox: dict, arts: list[dict]) -> float:
    x0, y0, w, h = bbox["x"], bbox["y"], bbox["w"], bbox["h"]
    area = max(w * h, 1e-9)
    best = 0.0
    for a in arts:
        b = a["bbox"]
        ix = max(0.0, min(x0 + w, b["x"] + b["w"]) - max(x0, b["x"]))
        iy = max(0.0, min(y0 + h, b["y"] + b["h"]) - max(y0, b["y"]))
        best = max(best, ix * iy / area)
    return best


def _node_text(el) -> str:
    return " ".join(" ".join(el.itertext()).split())


def _set_text(el, text: str):
    for ch in list(el):
        el.remove(ch)
    el.text = text


def apply_degradation(full_html: str, label: dict) -> tuple[str, dict]:
    """Retorna (html completo com [ilegível] + <aside>s, relatório)."""
    arts = [
        o for o in label.get("layout", {}).get("special_objects", [])
        if o.get("type") in ARTIFACT_TYPES and o.get("page", 1) == 1
    ]
    report = {"artifacts": [a["type"] for a in arts], "occluded_nodes": 0}
    if not arts:
        return full_html, report

    doc = lxml.html.document_fromstring(full_html)
    els = [e for e in label.get("elements", []) if e.get("page", 1) == 1 and e.get("text")]

    # 1) campos cobertos -> [ilegível] (só quando a correspondência é inequívoca)
    nodes = doc.xpath(_TEXT_TAGS)
    node_count = Counter(_norm(_node_text(n)) for n in nodes)
    occluded = Counter(_norm(e["text"]) for e in els if _covered_ratio(e["bbox"], arts) >= 0.5)
    for n in nodes:
        key = _norm(_node_text(n))
        if len(key) >= 3 and occluded.get(key, 0) >= node_count[key]:
            _set_text(n, ILLEGIBLE)
            report["occluded_nodes"] += 1

    # 2) âncora vertical de cada bloco do <article> (y médio dos textos únicos)
    by_text: dict[str, list[dict]] = {}
    for e in els:
        by_text.setdefault(_norm(e["text"]), []).append(e)
    article = doc.find(".//article")
    blocks = [c for c in article if isinstance(c.tag, str) and c.tag != "hr"]
    anchors = []
    for b in blocks:
        ys = []
        for n in b.xpath(_TEXT_TAGS):
            key = _norm(_node_text(n))
            hits = by_text.get(key, [])
            if len(key) >= 4 and len(hits) == 1 and node_count.get(key, 0) <= 1:
                ys.append(hits[0]["bbox"]["y"] + hits[0]["bbox"]["h"] / 2)
        anchors.append(sum(ys) / len(ys) if ys else None)

    # 3) <aside> após o último bloco ancorado acima do centro do artefato
    for a in sorted(arts, key=lambda o: (o["bbox"]["y"], o["bbox"]["x"])):
        yc = a["bbox"]["y"] + a["bbox"]["h"] / 2
        pos = -1
        for i, y in enumerate(anchors):
            if y is not None and y <= yc:
                pos = i
        marker = lxml.html.Element("img")  # só a sinalização: imagem sem conteúdo
        marker.set("data-kind", a["type"])
        if pos < 0:
            article.insert(0, marker)
        else:
            blocks[pos].addnext(marker)
            blocks.insert(pos + 1, marker)
            anchors.insert(pos + 1, None)
    return lxml.html.tostring(doc, encoding="unicode", doctype="<!DOCTYPE html>"), report
