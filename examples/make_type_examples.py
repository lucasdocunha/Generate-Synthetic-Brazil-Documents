"""Um exemplo de cada tipo de documento e de cada variação -> examples/types/ e examples/tipos.md.

    python examples/make_type_examples.py

Usa o pipeline unificado (generate_one com html=True), seed fixa. Mantém só uma
amostra por variação, com imagens reduzidas.
"""
from __future__ import annotations

import shutil
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PIL import Image  # noqa: E402

from pipeline.single import generate_one  # noqa: E402

OUT = ROOT / "examples" / "types"
SEED = 2026
# (tipo, variação, gen_opts, descrição)
CASES = [
    ("danfe", "linx_autosystem", {"erp_preset": "linx_autosystem"}, "ERP Linx: colunas de combustível (ANP), tabela com grade vertical, crédito no rodapé"),
    ("danfe", "xpert", {"erp_preset": "xpert"}, "ERP Xpert: coluna VALOR LÍQ., crédito no emitente e no rodapé"),
    ("danfe", "galago", {"erp_preset": "galago"}, "ERP Galago: ISSQN, logo e crédito no meio da página"),
    ("danfe", "minimal_open", {"erp_preset": "minimal_open"}, "Tabela de itens aberta embaixo, sem moldura inferior"),
    ("danfe", "classic_landscape", {"erp_preset": "classic_landscape"}, "DANFE em paisagem com canhoto lateral"),
    ("danfe", "padrao", {"erp_preset": "standard"}, "Layout padrão (sem ERP específico)"),
    ("nfe_portal", "classic_fazenda", {"variant": "classic_fazenda"}, "Consulta clássica do Portal Nacional (cartões bege)"),
    ("nfe_portal", "modern_svrs", {"variant": "modern_svrs"}, "Consulta moderna do Portal SVRS (cartões brancos)"),
    ("dacte", "dutoviario", {}, "CT-e do modal dutoviário (único modal gerado hoje)"),
    ("damdfe", "aereo", {}, "MDF-e do modal aéreo (único modal gerado hoje)"),
    ("danfse", "padrao", {}, "DANFSe v2.0 (NFS-e nacional)"),
    ("dacce", "padrao", {}, "Carta de correção eletrônica"),
    ("nfse_legado", "ginfes", {"city_layout": "ginfes"}, "NFS-e legada, leiaute de referência Ginfes v03 (lote de RPS)"),
    ("nfse_legado", "sao_paulo", {"city_layout": "sao_paulo"}, "São Paulo: brasão, caixa número/data/código, Intermediário, retenções e Outras Informações"),
    ("nfse_legado", "porto_velho", {"city_layout": "porto_velho"}, "Porto Velho (molde de notas reais): Prestador/Tomador, código do serviço, retenções federais"),
    ("nfse_legado", "fortaleza", {"city_layout": "fortaleza"}, "Fortaleza: grade de identificação, detalhamento de valores e cálculo do ISSQN"),
    ("nfse_legado", "maceio", {"city_layout": "maceio"}, "Maceió: Secretaria de Economia, prestador/tomador e quadro de valores"),
    ("nfse_legado", "rio_branco", {"city_layout": "rio_branco"}, "Rio Branco: Secretaria de Finanças e campos rótulo: valor"),
    ("nfse_legado", "generico_faixa", {"city_layout": "generico_faixa"}, "Estilo genérico (inventado, não é de uma cidade)"),
    ("nfse_legado", "generico_tabela", {"city_layout": "generico_tabela"}, "Estilo genérico (inventado, não é de uma cidade)"),
    ("nfse_legado", "generico_grade", {"city_layout": "generico_grade"}, "Estilo genérico (inventado, não é de uma cidade)"),
    ("nfse_legado", "generico_pontilhado", {"city_layout": "generico_pontilhado"}, "Estilo genérico (inventado, não é de uma cidade)"),
    ("nfse_legado", "generico_colunas", {"city_layout": "generico_colunas"}, "Estilo genérico (inventado, não é de uma cidade)"),
]


def shrink(path: Path):
    im = Image.open(path).convert("RGB")
    if im.width > 820:
        im = im.resize((820, round(im.height * 820 / im.width)), Image.LANCZOS)
    im.save(path.with_suffix(".jpg"), quality=78, optimize=True)
    path.unlink()


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    rows = []
    for doctype, variant, opts, desc in CASES:
        d = OUT / f"{doctype}__{variant}"
        # primeira amostra de página única (quando existir) com esta variação
        for idx in range(0, 12):
            row = generate_one(doctype, "train", idx, SEED, d, dpi_options=(110,), generate_geometric_variant=False,
                               force=True, gen_opts=opts, html=True)
            if row and (row["n_pages"] == 1 or idx == 11):
                break
        for png in list(d.rglob("*.png")):
            shrink(png)
        shutil.rmtree(d / doctype / "pdfs", ignore_errors=True)
        rows.append((doctype, variant, desc, row["n_pages"], row["text_fidelity"], f"{doctype}__{variant}"))

    lines = ["# Um exemplo de cada tipo de documento e suas variações", "",
             "Gerado por `python examples/make_type_examples.py` (pipeline unificado, `--html`, seed 2026).",
             "Cada pasta em [`types/`](types/) tem a estrutura de saída completa: `images/` (limpa) ↔ `html_clean/`, `md/`; "
             "`images_aug/` (degradada) ↔ `html_visible/`, `md_visible/`; `html/`, `xml/`, `labels/`, `metadata/`.", "",
             "| Tipo | Variação | O que muda | Págs. | Fidelidade | Imagem | HTML-alvo |", "|---|---|---|---|---|---|---|"]
    for doctype, variant, desc, npg, fid, folder in rows:
        sid = next((d.name for d in (OUT / folder / doctype / "html_clean" / "0000").glob("*.html")), None)
        stem = Path(sid).stem if sid else ""
        base = f"types/{folder}/{doctype}"
        lines.append(f"| `{doctype}` | `{variant}` | {desc} | {npg} | {fid} | "
                     f"[limpa]({base}/images/0000/{stem}_p1.jpg) · [degradada]({base}/images_aug/0000/{stem}.jpg) | "
                     f"[html_clean]({base}/html_clean/0000/{stem}.html) · [md]({base}/md/0000/{stem}.md) · "
                     f"[html_visible]({base}/html_visible/0000/{stem}.html) |")
    lines += ["", "## Prévia (imagens degradadas)", ""]
    for doctype, variant, _d, _n, _f, folder in rows:
        sid = next((d.stem for d in (OUT / folder / doctype / "html_clean" / "0000").glob("*.html")), "")
        lines.append(f"**{doctype} / {variant}**  \n![{doctype} {variant}](types/{folder}/{doctype}/images_aug/0000/{sid}.jpg)\n")
    (ROOT / "examples" / "tipos.md").write_text("\n".join(lines), encoding="utf8")
    print("ok")


if __name__ == "__main__":
    main()
