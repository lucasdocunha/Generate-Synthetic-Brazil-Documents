"""Renderiza uma NFS-e a partir de um molde (JSON) extraído de notas reais da prefeitura
(ver tools/build_nfse_specs.py): linhas/retângulos/preenchimentos e rótulos fixos nas posições
originais, e campos de valor preenchidos com os dados sintéticos conforme o rótulo vizinho."""

from __future__ import annotations

import json
import random
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

SPEC_DIR = Path(__file__).parent / "nfse_cidades_specs"
_FAM = {"helvetica": "Helvetica", "times": "Times", "courier": "Courier"}


def has_spec(city: str) -> bool:
    return (SPEC_DIR / f"{city}.json").exists()


@lru_cache(maxsize=None)
def load_spec(city: str) -> dict:
    return json.loads((SPEC_DIR / f"{city}.json").read_text("utf8"))


def _n(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().upper()


def _context(spec, slot):
    """(rótulo vizinho normalizado, seção prestador/tomador/intermediário)."""
    best, bd = "", 1e9
    for f in spec["fixed"]:
        fy, fx0, fx1 = f["y"], f["x"], f["x1"]
        above = 0 < slot["y"] - fy < 7 and fx0 - 2 <= slot["x1"] and fx1 >= slot["x0"] - 2
        left = abs(slot["y"] - fy) < 1.5 and fx1 <= slot["x0"] + 1.5 and slot["x0"] - fx1 < 70
        if above or left:
            d = (slot["y"] - fy) if above else (slot["x0"] - fx1) * 0.6
            if d < bd and len(f["text"]) <= 60:
                best, bd = f["text"], d
    sec, sd = "", 1e9
    for f in spec["fixed"]:
        t = _n(f["text"])
        if any(k in t for k in ("PRESTADOR", "TOMADOR", "INTERMEDI")) and f["y"] <= slot["y"] + 1 and slot["y"] - f["y"] < sd and len(t) < 70:
            sd, sec = slot["y"] - f["y"], ("P" if "PRESTADOR" in t else "T" if "TOMADOR" in t else "I")
    return _n(best), sec


def _value(slot, label, sec, d, rng):
    L = label
    if slot.get("lines", 1) > 1 or "DISCRIMINA" in L or (slot["len"] > 170 and not re.search(r"RAZAO|NOME", L)):
        return d["disc"]
    t = slot["type"]
    person = {"P": ("prest", "prest_doc"), "T": ("tom", "tom_doc"), "I": ("", "")}.get(sec, ("prest", "prest_doc"))
    if "FANTASIA" in L:
        return d["prest"] if sec == "P" else ""
    if re.search(r"NUMERO.*(NOTA|NFS)|N[O°º]? ?NFS|NFS-?E ?N|NFS-?E:|NUMERO DA NFS", L) or (L.strip() in ("NUMERO", "NUMERO DA NOTA", "NUMERO DA") and t in ("int", "numlike")):
        return d["nota_seq"]
    if "VERIFICACAO" in L:
        return d["cod"]
    if "OBRA" in L:  # número do endereço não é inscrição de obra
        return ""
    if "COMPETENCIA" in L:
        return d["comp"]
    if "RPS" in L or "SUBSTITU" in L:
        return ""
    if re.search(r"DATA|EMISS|EMITIDA|HORA", L) or t == "date":
        return d["datahora"] if (t == "date" and slot["len"] > 12) or "HORA" in L else d["data"]
    if "CNPJ" in L or "CPF" in L:
        return d[person[1]] if person[1] else ""
    if "INSCRICAO MUN" in L or "INSC MUN" in L or "CCM" in L or "MOBILIARIO" in L:
        return d["im"] if sec == "P" else ""
    if "INSCRICAO ESTADUAL" in L or "INSC ESTADUAL" in L or "ESTADUAL" in L:
        return ""
    if re.search(r"RAZAO|NOME", L):
        return d[person[0]] if person[0] else ""
    if "ENDERECO" in L or "LOGRADOURO" in L:
        return d["street"] if sec != "T" else d["street"]
    if "COMPLEMENTO" in L:
        return ""
    if "BAIRRO" in L:
        return d["bairro"]
    if re.search(r"CIDADE|MUNICIPIO", L):
        return d["mun"]
    if re.fullmatch(r".*\bUF\b.*", L) or L.strip() == "UF":
        return d["uf"]
    if "CEP" in L:
        return d["cep"]
    if "MAIL" in L:
        return d["email"]
    if re.search(r"TELEFONE|FONE|TEL\b", L):
        return d["fone"]
    if "NUMERO" in L:
        return d["numero"]
    if "ALIQUOTA" in L:
        return d["aliq"]
    if re.search(r"VALOR (DO |DA )?(ISS|ISSQN)|ISS ?\(|ISSQN", L) and "RETIDO" not in L and "RETER" not in L:
        return d["iss"]
    if "BASE" in L:
        return d["valor"]
    if re.search(r"RETEN|DEDU|DESCONTO|PIS|COFINS|INSS|IRRF|\bIR\b|CSLL|CREDITO|OUTRAS|APROXIMADO", L):
        return "0,00"
    if re.search(r"VALOR|TOTAL|LIQUIDO|SERVICO", L) and t == "money":
        return d["valor"]
    if "CODIGO" in L and ("SERVICO" in L or "ATIVIDADE" in L):
        return f"{d['item']} - {d['disc']}"
    # por tipo
    if t == "money":
        return d["valor"] if slot["n"] and "VALOR" in L else "0,00"
    if t == "int":
        return str(rng.randint(10 ** (slot["len"] - 1), 10 ** slot["len"] - 1)) if slot["len"] > 0 else ""
    if t == "doc":
        return ""
    return ""


def _fit(pdf, txt, w):
    """Corta o texto até caber em w (na fonte atual)."""
    while txt and pdf.get_string_width(txt) > w:
        txt = txt[:-1]
    return txt


def render_spec(pdf, city: str, d: dict):
    spec = load_spec(city)
    rng = random.Random(d["nota"] + city)
    from_rgb = lambda c: ((c >> 16) & 255, (c >> 8) & 255, c & 255)  # noqa: E731

    # --- desenho vetorial
    for s in spec["draws"]:
        st, fl = s.get("stroke"), s.get("fill")
        pdf.set_line_width(max(s.get("w") or 0.2, 0.05))
        if st is not None:
            pdf.set_draw_color(*[round(v * 255) for v in st])
        if fl is not None:
            pdf.set_fill_color(*[round(v * 255) for v in fl])
        dash = [float(x) for x in re.findall(r"[\d.]+", s.get("dash") or "")[:-1]] if "[" in (s.get("dash") or "") else []
        if dash and sum(dash) > 0:
            pdf.set_dash_pattern(dash=dash[0] * 0.3528, gap=(dash[1] if len(dash) > 1 else dash[0]) * 0.3528)
        x0, y0, x1, y1 = s["b"]
        if s["t"] == "re":
            if fl is not None or st is not None:
                pdf.rect(x0, y0, x1 - x0, y1 - y0, style="DF" if (fl is not None and st is not None) else "F" if fl is not None else "D")
        elif st is not None:
            pdf.line(x0, y0, x1, y1)
        pdf.set_dash_pattern(dash=0, gap=0)
    pdf.set_draw_color(0, 0, 0)

    drawn = []
    def text(x, y, w, txt, size, bold, font, color, align="L"):
        fam, style = _FAM.get(font, "Helvetica"), "B" if bold else ""
        pdf.set_text_color(*from_rgb(color or 0))
        if w:  # diminui a fonte até caber; só corta se nem o menor tamanho couber
            pdf.set_font(fam, style, size)
            while size > 5 and pdf.get_string_width(txt) > w:
                size -= 0.25
                pdf.set_font(fam, style, size)
            txt = _fit(pdf, txt, w)
        pdf.set_font(fam, style, size)
        tw = pdf.get_string_width(txt)
        xx = x if align == "L" or not w else (x + w - tw if align == "R" else x + (w - tw) / 2)
        if any(t == txt and abs(dx - xx) < 2 and abs(dy - y) < 2 for dx, dy, t in drawn):  # mesmo texto no mesmo lugar
            return
        drawn.append((xx, y, txt))
        pdf.text(xx, y, txt)

    # --- rótulos fixos
    for f in spec["fixed"]:
        text(f["x"], f["y"], 0, f["text"], f["size"], f["bold"], f["font"], f["color"])

    # --- campos de valor
    iss_shown = False  # a nota traz um único valor de ISS; campos extras de ISS ficam vazios
    for s in spec["slots"]:
        label, sec = _context(spec, s)
        val = _value(s, label, sec, d, rng) or ""
        if re.search(r"\bISS", label) and val:  # \b: não pega EMISSAO
            val, iss_shown = ("" if iss_shown else val), True
        if not label and s["x0"] > 180:  # campo sem rótulo na borda direita: fica de fora
            val = ""
        if s.get("lines", 1) > 1:
            # o bloco de texto para antes de um rótulo fixo que esteja ao lado dele
            x1 = min([s["x1"]] + [f["x"] - 1 for f in spec["fixed"]
                                  if s["top"] <= f["y"] <= s["bot"] and s["x0"] + 1 < f["x"] < s["x1"]])
            pdf.set_font(_FAM.get(s["font"], "Helvetica"), "B" if s["bold"] else "", s["size"])
            pdf.set_text_color(*from_rgb(s["color"] or 0))
            lh = (s["bot"] - s["top"]) / s["lines"]
            pdf.set_xy(s["x0"], s["top"])
            maxh = s["bot"] - s["top"] + 8
            lines = pdf.multi_cell(x1 - s["x0"], lh, val, dry_run=True, output="LINES")
            keep = int(maxh // lh)
            pdf.set_xy(s["x0"], s["top"])
            pdf.multi_cell(x1 - s["x0"], lh, " ".join(lines[:keep]) if len(lines) > keep else val)
        else:
            wlim = (s["x1"] - s["x0"]) if s["type"] != "text" else min(max(s["x1"] - s["x0"], 70), 204 - s["x0"])
            # o campo para antes do próximo rótulo na mesma linha, se sobrar espaço útil (>= 12 mm)
            right = [f["x"] for f in spec["fixed"] if abs(f["y"] - s["y"]) < 3 and f["x"] > s["x0"] + 1]
            cap = min([204] + right) - s["x0"] - 1
            if cap >= 12 and (cap < wlim or ("SERVICO" in label and "CODIGO" in label)):
                wlim = cap
            elif re.fullmatch(r"[\d.,]+", val):  # valor numérico não pode ser cortado: dá uma largura mínima
                wlim = max(wlim, 10)
            text(s["x0"], s["y"], wlim, val, s["size"], s["bold"], s["font"], s["color"], s["align"])
    pdf.set_text_color(0, 0, 0)

    # --- QR sintético onde havia imagem quadrada
    import qrcode

    for x0, y0, x1, y1 in spec["imgs"]:
        w, h = x1 - x0, y1 - y0
        if 15 < w < 45 and 0.85 < w / h < 1.18:
            img = qrcode.make(f"https://nfse.sintetico.invalid/verifica?c={d['cod']}").get_image()
            pdf.image(img, x=x0, y=y0, w=w, h=h)
