"""Gera os exemplos da NFS-e legada (Ginfes v03) e escreve examples/nfse_legado.md
a partir da saída real.

    python examples/make_nfse_examples.py

Gera 3 amostras com seed fixa (HTML/Markdown incluídos) numa pasta temporária,
copia um subconjunto para examples/dataset/nfse_legado/ (imagens reduzidas para
1240 px de largura, como no resto do dataset de exemplo) e reescreve o .md com
trechos reais de XML, label, KIE e Markdown.
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import warnings
from pathlib import Path
from xml.dom import minidom

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PIL import Image  # noqa: E402

from pipeline.single import generate_one  # noqa: E402

EX = ROOT / "examples"
DATASET = EX / "dataset" / "nfse_legado"
SEED = 2026
INDICES = [("train", 0), ("train", 1), ("test", 2)]
MAX_W = 1240
SUBDIRS = ["xml", "pdfs", "images", "images_aug", "labels", "metadata", "html_clean", "md",
           "html_visible", "md_visible", "html"]


def _reduce(src: Path, dst: Path):
    dst.parent.mkdir(parents=True, exist_ok=True)
    im = Image.open(src)
    if im.width > MAX_W:
        im = im.resize((MAX_W, round(im.height * MAX_W / im.width)), Image.LANCZOS)
    im.save(dst, optimize=True)


def _pretty_xml(path: Path) -> str:
    return minidom.parseString(path.read_bytes()).toprettyxml(indent="  ").strip()


def main():
    out = Path(tempfile.mkdtemp(prefix="nfse_examples_"))
    rows = []
    for split, index in INDICES:
        rows.append(generate_one("nfse_legado", split, index, SEED, out, dpi_options=(150,),
                                 generate_geometric_variant=False, force=True, html=True))

    if DATASET.exists():
        shutil.rmtree(DATASET)
    base = out / "nfse_legado"
    for row in rows:
        sid = row["doc_id"]
        shard = "0000"
        for sub in SUBDIRS:
            for f in base.rglob(f"{sub}/{shard}/{sid}*"):
                rel = f.relative_to(base)
                dst = DATASET / rel
                if f.suffix == ".png" and sub in ("images", "images_aug"):
                    _reduce(f, dst)
                else:
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(f, dst)
    # PDF de referência (um só) na pasta de PDFs de exemplo
    first = rows[0]["doc_id"]
    shutil.copy2(base / "pdfs" / "0000" / f"{first}.pdf", EX / "pdfs" / "nfse_legado.pdf")

    _write_doc(base, rows, first)
    shutil.rmtree(out, ignore_errors=True)
    print(f"ok: {len(rows)} amostras em {DATASET.relative_to(ROOT)} e examples/nfse_legado.md")


def _write_doc(base: Path, rows, first: str):
    label = json.loads((base / "labels" / "0000" / f"{first}.json").read_text("utf8"))
    meta = json.loads((base / "metadata" / "0000" / f"{first}.meta.json").read_text("utf8"))
    xml = _pretty_xml(base / "xml" / "0000" / f"{first}.xml")
    xml_head = "\n".join(xml.splitlines()[:28])
    kie = json.dumps(label["kie"], ensure_ascii=False, indent=2)
    elems = [e for e in label["elements"] if e["field_ids"]][:6]
    elems_txt = "\n".join(
        f'{e["bbox"]["x"]:6.1f} {e["bbox"]["y"]:6.1f} {e["bbox"]["w"]:6.1f} {e["bbox"]["h"]:5.1f}  '
        f'{",".join(e["field_ids"]):<22} {e["text"]}' for e in elems
    )
    md = (base / "md_visible" / "0000" / f"{first}.md").read_text("utf8")
    md_head = "\n".join(md.splitlines()[:30])
    rows_txt = "\n".join(
        f'| `{r["doc_id"]}` | {r["split"]} | {r["match_rate"]:.2f} | {r["text_fidelity"]:.2f} |'
        for r in rows
    )
    stamps = [o["type"] for o in label["layout"].get("special_objects", [])]
    occl = meta.get("html", {}).get("occlusion", {})

    text = f"""# NFS-e legada (Ginfes v03): exemplos

Lote de RPS (*Recibo Provisório de Serviços*) no padrão municipal legado, anterior ao ADN
nacional, gerado a partir do XML `EnviarLoteRpsEnvio` com os bindings da lib
`nfselib-legacy`. O PDF é um **leiaute de referência** deste repositório (não há
PDF oficial da prefeitura para esse envelope). Todo dado é sintético.

Gerado por `python examples/make_nfse_examples.py` (seed {SEED}, HTML/Markdown incluídos).

| Amostra | Split | `match_rate` | `text_fidelity` |
|---|---|---|---|
{rows_txt}

## 1. PDF e imagem

A página limpa (`images/`) e a degradada (`images_aug/`) da mesma amostra:

| Limpa | Degradada |
|---|---|
| ![limpa](dataset/nfse_legado/images/0000/{first}_p1.png) | ![degradada](dataset/nfse_legado/images_aug/0000/{first}.png) |

Objetos especiais sobrepostos nesta amostra (carimbo, assinatura, POS): `{", ".join(stamps) or "nenhum"}`,
registrados em `labels` como `special_objects` com a transcrição do texto.

## 2. XML de origem (verdade de campo)

Início de `xml/0000/{first}.xml`, identado só para leitura (o arquivo original é uma linha):

```xml
{xml_head}
```

## 3. Label: campos casados com o PDF

Cada campo é casado com o span de texto do PDF (`match_rate` = 1,0 quando todos casam).
Primeiras linhas com campo casado (`x y w h` em mm):

```
{elems_txt}
```

## 4. KIE

`kie` de `labels/0000/{first}.json`: a mesma informação, por papel, com a caixa de origem em `bbox_ref`.

```json
{kie}
```

## 5. Markdown visível (par de `images_aug/`)

`md_visible/0000/{first}.md`, primeiras linhas:

```markdown
{md_head}
```

O HTML limpo (`html_clean/`) segue a mesma ordem de blocos do PDF, e `html_visible/` marca os
campos cobertos por carimbo/POS como `[ilegível]` (oclusão aplicada: {occl.get("occluded_nodes", 0)} nós nesta amostra).

## 6. Como gerar

```bash
# 3 amostras com HTML/Markdown
python examples/make_nfse_examples.py

# lote completo: a seed de cada amostra deriva de (seed, tipo, split, índice)
python -m pipeline.cli generate --doctype nfse_legado --count 1000 --workers 8 --html --out dataset
```

Ver também [`README.md`](../README.md#8-exemplos-práticos) (uso em Python, ponto a ponto).
"""
    (EX / "nfse_legado.md").write_text(text, encoding="utf8")


if __name__ == "__main__":
    main()
