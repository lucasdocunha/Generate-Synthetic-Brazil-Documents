"""Constrói moldes (JSON) de NFS-e municipais a partir de PDFs reais da mesma prefeitura.

    python -I tools/build_nfse_specs.py <cidade> <pdf1> <pdf2> ... [--out renderers/nfse_cidades_specs]

Compara as notas: texto igual na mesma posição = RÓTULO FIXO; texto que muda = CAMPO DE VALOR
(com tipo inferido: data, valor, CNPJ/CPF, número, texto). Linhas, retângulos e preenchimentos
da nota-base são guardados em mm. Nada do conteúdo variável (nomes, valores) vai para o molde.
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
import fitz  # noqa: E402

MM = 25.4 / 72.0


def norm(s):
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().upper()


def font_key(n):
    n = n.lower()
    return "courier" if ("courier" in n or "mono" in n) else "times" if ("times" in n or "serif" in n) else "helvetica"


def extract(path):
    d = fitz.open(path)
    page = d[0]
    items = []
    for b in page.get_text("dict")["blocks"]:
        if b.get("type") != 0:
            continue
        for ln in b["lines"]:
            if abs(ln["dir"][0] - 1) > 0.02:
                continue
            cur = None
            for s in ln["spans"]:
                if not s["text"].strip():
                    if cur:
                        cur["text"] += s["text"]
                    continue
                style = (round(s["size"], 1), bool((s["flags"] & 16) or "bold" in s["font"].lower()), font_key(s["font"]), s.get("color", 0))
                bb = [v * MM for v in s["bbox"]]
                if cur and cur["style"] == style and bb[0] - cur["bbox"][2] < 2.0:
                    cur["text"] += s["text"]; cur["bbox"][2] = bb[2]; continue
                if cur:
                    items.append(cur)
                cur = {"text": s["text"], "bbox": bb, "origin": [v * MM for v in s["origin"]], "style": style, "size": s["size"],
                       "bold": style[1], "font": style[2], "color": style[3]}
            if cur:
                items.append(cur)
    for it in items:
        it["text"] = it["text"].strip()
    items = [i for i in items if i["text"]]
    draws = []
    for dr in page.get_drawings():
        for it in dr["items"]:
            if it[0] == "re":
                r = it[1]
                draws.append({"t": "re", "b": [r.x0 * MM, r.y0 * MM, r.x1 * MM, r.y1 * MM], "stroke": dr.get("color"), "fill": dr.get("fill"),
                              "w": (dr.get("width") or 0) * MM, "dash": dr.get("dashes") or ""})
            elif it[0] == "l":
                draws.append({"t": "l", "b": [it[1].x * MM, it[1].y * MM, it[2].x * MM, it[2].y * MM], "stroke": dr.get("color"),
                              "w": (dr.get("width") or 0) * MM, "dash": dr.get("dashes") or ""})
    imgs = [[v * MM for v in i["bbox"]] for i in page.get_image_info()]
    return {"size": [page.rect.width * MM, page.rect.height * MM], "items": items, "draws": draws, "imgs": imgs}


def vtype(samples):
    def is_(rx):
        return sum(bool(re.fullmatch(rx, s.strip())) for s in samples) >= max(1, 0.6 * len(samples))
    if is_(r"\d{2}/\d{2}/\d{4}(\s+(às\s+)?\d{2}:\d{2}(:\d{2})?)?"):
        return "date"
    if is_(r"(R\$\s*)?-?\d{1,3}(\.\d{3})*,\d{2,4}"):
        return "money"
    if is_(r"[\d./-]{11,18}"):
        return "doc"
    if is_(r"\d+"):
        return "int"
    if is_(r"[\d.,/-]+"):
        return "numlike"
    return "text"


DROP = ""


def build(city, paths):
    docs = [extract(p) for p in paths]
    base = sorted(docs, key=lambda d: len(d["items"]))[len(docs) // 2]
    others = [d for d in docs if d is not base]
    fixed, slots = [], []
    for it in base["items"]:
        cx, cy = (it["bbox"][0] + it["bbox"][2]) / 2, (it["bbox"][1] + it["bbox"][3]) / 2
        same, diff, samples, boxes = 0, 0, [it["text"]], [it["bbox"]]
        for o in others:
            near = [j for j in o["items"] if abs((j["bbox"][1] + j["bbox"][3]) / 2 - cy) < 1.2 and j["bbox"][0] - 1.5 <= cx <= j["bbox"][2] + 1.5]
            if not near:
                continue
            j = min(near, key=lambda j: abs((j["bbox"][0] + j["bbox"][2]) / 2 - cx))
            if j["text"] == it["text"]:
                same += 1
            else:
                diff += 1; samples.append(j["text"]); boxes.append(j["bbox"])
        base_el = {"x": it["bbox"][0], "y": it["origin"][1], "top": it["bbox"][1], "h": it["bbox"][3] - it["bbox"][1], "size": it["size"],
                   "bold": it["bold"], "font": it["font"], "color": it["color"], "text": it["text"], "x1": it["bbox"][2]}
        t_ = it["text"]
        forced_label = len(t_) <= 70 and (t_.endswith(":") or (
            t_ == t_.upper() and not re.search(r"\d", t_) and re.search(
                r"SERVI|PRESTADOR|TOMADOR|DADOS|VALOR|DISCRIMINA|C[OÓ]DIGO|RETEN|INFORMA|OUTRAS|TRIBUT|DEDU|DETALHAM|AVISOS|NOTA FISCAL|PREFEITURA|SECRETARIA|C[AÁ]LCULO|IMPOSTO|OBSERVA|ATIVIDADE", t_)))
        forced_slot = bool(DROP and re.search(DROP, it["text"], re.I))
        if forced_slot:
            slots.append({**base_el, "x0": it["bbox"][0], "x1": it["bbox"][2], "align": "L", "type": "text", "n": 1, "len": len(it["text"])})
        elif not forced_label and diff >= 1 and diff >= 0.3 * (same + diff):
            x0 = it["bbox"][0]; x1 = max(b[2] for b in boxes)
            xs0 = [b[0] for b in boxes]; xs1 = [b[2] for b in boxes]
            align = "L" if max(xs0) - min(xs0) < 1.0 else "R" if max(xs1) - min(xs1) < 1.0 else "C"
            slots.append({**base_el, "x0": x0, "x1": x1, "align": align, "type": vtype(samples), "n": len(samples), "len": max(map(len, samples))})
        elif not re.search(r"[A-Za-zÀ-ú]", it["text"]):  # só números/símbolos: é valor, não rótulo
            slots.append({**base_el, "x0": it["bbox"][0], "x1": it["bbox"][2], "align": "R", "type": vtype(samples), "n": 1, "len": len(it["text"])})
        else:
            fixed.append(base_el)
    # fundir slots empilhados (parágrafos) com mesmo x0/estilo
    slots.sort(key=lambda s: (round(s["x0"]), s["top"]))
    merged = []
    for s in slots:
        m = merged[-1] if merged else None
        if m and abs(m["x0"] - s["x0"]) < 1.0 and s["font"] == m["font"] and abs(s["size"] - m["size"]) < 0.1 and 0 < s["top"] - m["bot"] < 2.5 and s["type"] == "text":
            m["bot"] = s["top"] + s["h"]; m["lines"] += 1; m["x1"] = max(m["x1"], s["x1"]); continue
        merged.append({**s, "bot": s["top"] + s["h"], "lines": 1})
    spec = {"city": city, "size": base["size"], "draws": base["draws"], "fixed": fixed, "slots": merged,
            "imgs": base["imgs"], "n_docs": len(docs)}
    return spec


if __name__ == "__main__":
    city, *rest = sys.argv[1:]
    if "--drop" in rest:  # regex de textos de uma empresa específica que vazaram como "fixos"
        i = rest.index("--drop"); DROP = rest[i + 1]; rest = rest[:i] + rest[i + 2:]
    out = Path("renderers/nfse_cidades_specs")
    if "--out" in rest:
        i = rest.index("--out"); out = Path(rest[i + 1]); rest = rest[:i]
    spec = build(city, rest)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{city}.json").write_text(json.dumps(spec, ensure_ascii=False))
    print(city, "fixos", len(spec["fixed"]), "campos", len(spec["slots"]), "desenhos", len(spec["draws"]), "imagens", len(spec["imgs"]))
