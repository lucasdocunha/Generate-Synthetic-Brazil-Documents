"""Grava os artefatos de uma amostra na árvore <out>/<doctype>/ (PLANO_GERADOR.md
secao 2.2). O `metadata/*.meta.json` é escrito por ÚLTIMO e atomicamente
(escreve em .tmp, depois os.replace) — é o único critério de "amostra pronta"
usado pelo checkpoint/resume do batch driver (secao 3.2/15).

Nomenclatura (igual para todos os tipos):
  images/<id>_p<N>.png   página N limpa            <-> html_clean/, md/
  images_aug/<id>.png    página 1 degradada        <-> html_visible/, md_visible/
  images_geo/<id>.png    variante geométrica (sem boxes válidas)
  html/<id>.html         HTML com CSS (reproduz a imagem limpa no Chromium)
  xml/ pdfs/ labels/ metadata/ e manifest.parquet
"""

import json
import os
from pathlib import Path

from export.sharding import shard_dir

# chave -> (subpasta, sufixo)
ARTIFACTS = {
    "xml": ("xml", ".xml"),
    "pdf": ("pdfs", ".pdf"),
    "image_aug": ("images_aug", ".png"),
    "image_geo": ("images_geo", ".png"),
    "label": ("labels", ".json"),
    "meta": ("metadata", ".meta.json"),
    "html": ("html", ".html"),
    "html_clean": ("html_clean", ".html"),
    "md": ("md", ".md"),
    "html_visible": ("html_visible", ".html"),
    "md_visible": ("md_visible", ".md"),
}
TEXT_KEYS = ("html", "html_clean", "md", "html_visible", "md_visible")


def _atomic_write_bytes(path: Path, data: bytes):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def _atomic_write_text(path: Path, text: str):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf8")
    os.replace(tmp, path)


def sample_paths(out_dir: Path, doctype: str, index: int, sid: str) -> dict:
    shard, base = shard_dir(index), Path(out_dir) / doctype
    paths = {k: base / sub / shard / f"{sid}{ext}" for k, (sub, ext) in ARTIFACTS.items()}
    paths["images_dir"] = base / "images" / shard
    return paths


def page_image_path(out_dir: Path, doctype: str, index: int, sid: str, page: int) -> Path:
    return sample_paths(out_dir, doctype, index, sid)["images_dir"] / f"{sid}_p{page}.png"


def is_sample_done(out_dir: Path, doctype: str, index: int, sid: str) -> bool:
    """Critério único de checkpoint/resume: o meta.json só existe se TODA a
    amostra foi exportada com sucesso."""
    meta_path = sample_paths(out_dir, doctype, index, sid)["meta"]
    if not meta_path.exists():
        return False
    try:
        json.loads(meta_path.read_text(encoding="utf8"))
        return True
    except (json.JSONDecodeError, OSError):
        return False


def write_sample(
    out_dir: Path,
    doctype: str,
    index: int,
    sid: str,
    xml_str: str,
    pdf_bytes: bytes,
    page_images: list,
    image_aug,
    image_geo,
    label: dict,
    meta: dict,
    texts: dict | None = None,
):
    """`texts`: subconjunto de TEXT_KEYS -> conteúdo (html/md), quando `--html`."""
    paths = sample_paths(out_dir, doctype, index, sid)
    paths["images_dir"].mkdir(parents=True, exist_ok=True)
    always = {"xml", "pdf", "image_aug", "image_geo", "label", "meta"} | set(texts or {})
    for k in always:
        paths[k].parent.mkdir(parents=True, exist_ok=True)

    _atomic_write_text(paths["xml"], xml_str)
    _atomic_write_bytes(paths["pdf"], pdf_bytes)
    for n, im in enumerate(page_images, 1):
        im.save(page_image_path(out_dir, doctype, index, sid, n), format="PNG")
    image_aug.save(paths["image_aug"], format="PNG")
    if image_geo is not None:
        image_geo.save(paths["image_geo"], format="PNG")
    for key, content in (texts or {}).items():
        _atomic_write_text(paths[key], content)
    _atomic_write_text(paths["label"], json.dumps(label, ensure_ascii=False, indent=2))
    # meta.json por ÚLTIMO — é o sinal de "amostra pronta" (ver is_sample_done)
    _atomic_write_text(paths["meta"], json.dumps(meta, ensure_ascii=False, indent=2))

    return paths
