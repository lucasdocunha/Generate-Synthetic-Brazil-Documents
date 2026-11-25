"""Gera examples/galeria.md: uma imagem de cada tipo, variação e efeito do gerador.

    python examples/make_galeria.py

Lê examples/types/<tipo__variacao>/ e examples/effects/<efeito>/ (saídas reais de
examples/make_type_examples.py e examples/make_effect_examples.py) e escreve a galeria
com a página limpa e a degradada de cada tipo, e o antes/depois de cada efeito.
"""

from __future__ import annotations

import re
from pathlib import Path

EX = Path(__file__).resolve().parent
OUT = EX / "galeria.md"
IMG_W = 330

TYPE_LABEL = {
    "dacce": "DACCe (carta de correção)",
    "dacte": "DACTE (CT-e)",
    "damdfe": "DAMDFE (MDF-e)",
    "danfe": "DANFE (NF-e)",
    "danfse": "DANFSe v2.0 (NFS-e nacional)",
    "nfe_portal": "Consulta do Portal da NF-e",
    "nfse_legado": "NFS-e legada (Ginfes v03)",
}

VARIANT_LABEL = {
    "padrao": "padrão",
    "dutoviario": "modal dutoviário",
    "aereo": "modal aéreo",
    "classic_landscape": "ERP paisagem clássico",
    "galago": "ERP Galago",
    "linx_autosystem": "ERP Linx/Autosystem",
    "minimal_open": "ERP minimal (aberto)",
    "xpert": "ERP Xpert",
    "classic_fazenda": "clássico (Fazenda)",
    "modern_svrs": "moderno (SVRS)",
    "ginfes": "Ginfes (leiaute de referência)",
    "fortaleza": "Fortaleza",
    "maceio": "Maceió",
    "porto_velho": "Porto Velho",
    "rio_branco": "Rio Branco",
    "sao_paulo": "São Paulo",
    "generico_colunas": "genérico: duas colunas",
    "generico_faixa": "genérico: faixa de título",
    "generico_grade": "genérico: grade completa",
    "generico_pontilhado": "genérico: campos pontilhados",
    "generico_tabela": "genérico: rótulo sombreado",
}

EFFECT_LABEL = {
    "assinatura": "Assinatura sobre o texto",
    "carimbo_cnpj": "Carimbo com CNPJ",
    "carimbo_recebimento": "Carimbo de recebimento",
    "comprovante_pos": "Comprovante de POS",
    "inclinacao": "Inclinação da página",
    "modos_scanner": "Modos de scanner",
    "oclusao_html": "Oclusão no HTML (html_visible)",
    "riscos_dobra_bordas": "Riscos, dobras e bordas",
    "variante_geometrica": "Variante com distorção geométrica",
}

SCAN_LABEL = {
    "clean_digital": "digital limpo",
    "color_scan": "scanner colorido",
    "bw_binarized_scan": "scanner P&B binarizado",
}

CARIMBO_LABEL = {
    "estilo_blue_recebemos": "estilo azul (“Recebemos”)",
    "estilo_classic_em_de": "estilo clássico (“em/de”)",
    "estilo_status_box": "estilo caixa de status",
}

RISCO_LABEL = {
    "so_bordas": "somente bordas",
    "so_dobra": "somente dobra",
    "so_riscos": "somente riscos",
}


def _key(path: Path) -> int:
    m = re.search(r"_p(\d+)\.", path.name)
    return int(m.group(1)) if m else 0


def _img(path: Path) -> str:
    rel = path.relative_to(EX).as_posix()
    return f'<img src="{rel}" width="{IMG_W}" alt="{path.stem}">'


def _row(cells: list[str]) -> str:
    return "| " + " | ".join(cells) + " |"


def _types_section() -> list[str]:
    lines = [
        "## 1. Tipos e variações",
        "",
        "Cada tipo e variação aparece como **página limpa** (`images/`, o documento como ele é) e "
        "**página degradada** (`images_aug/`, com scanner, inclinação e demais efeitos). Quando o "
        "documento tem mais de uma página, todas são mostradas.",
        "",
    ]
    for folder in sorted((EX / "types").iterdir()):
        if not folder.is_dir():
            continue
        doctype, _, variant = folder.name.partition("__")
        title = f"{TYPE_LABEL.get(doctype, doctype)} · {VARIANT_LABEL.get(variant, variant or 'padrão')}"
        clean = sorted((folder / doctype / "images").rglob("*.jpg"), key=lambda p: (p.name, _key(p)))
        aug = sorted((folder / doctype / "images_aug").rglob("*.jpg"))
        lines += [f"### {title}", "", _row(["Limpa", "Degradada"]), _row(["---", "---"])]
        pages = [p for p in clean if p.name.startswith(f"{doctype}_train_00000000")] or clean[:1]
        pages = sorted(pages, key=_key)
        degraded = aug[:1]
        rows = max(len(pages), len(degraded))
        for i in range(rows):
            left = _img(pages[i]) if i < len(pages) else ""
            right = _img(degraded[0]) if i == 0 and degraded else ""
            lines.append(_row([left, right]))
        lines.append("")
    return lines


def _effects_section() -> list[str]:
    lines = [
        "## 2. Efeitos de degradação",
        "",
        "Antes e depois de cada efeito, sobre o mesmo DANFE com seed fixa. Os parâmetros e o "
        "comando de cada um estão em [`README.md`](README.md).",
        "",
    ]
    for folder in sorted((EX / "effects").iterdir()):
        if not folder.is_dir():
            continue
        lines += [f"### {EFFECT_LABEL.get(folder.name, folder.name)}", ""]
        files = sorted(folder.glob("*.jpg"))
        ba = [f for f in files if f.stem in ("antes", "depois")]
        variants = [f for f in files if f.stem not in ("antes", "depois")]
        if ba:
            lines += [_row(["Antes", "Depois"]), _row(["---", "---"])]
            antes = next((f for f in ba if f.stem == "antes"), None)
            depois = next((f for f in ba if f.stem == "depois"), None)
            lines.append(_row([_img(antes) if antes else "", _img(depois) if depois else ""]))
            lines.append("")
        if variants:
            labels = {**SCAN_LABEL, **CARIMBO_LABEL, **RISCO_LABEL}
            lines += [_row([labels.get(f.stem, f.stem) for f in variants]),
                      _row(["---"] * len(variants))]
            lines.append(_row([_img(f) for f in variants]))
            lines.append("")
    return lines


def main():
    head = [
        "# Galeria de exemplos visuais",
        "",
        "Imagens reais geradas pelo pipeline, uma de cada tipo, variação e efeito. Dados sintéticos; "
        "os documentos não têm validade fiscal. Regenerar com `python examples/make_galeria.py` "
        "(depende de `make_type_examples.py` e `make_effect_examples.py`).",
        "",
    ]
    text = "\n".join(head + _types_section() + _effects_section())
    OUT.write_text(text, encoding="utf8")
    n = len(re.findall(r"<img ", text))
    print(f"ok: {OUT.relative_to(EX.parent)} com {n} imagens")


if __name__ == "__main__":
    main()
