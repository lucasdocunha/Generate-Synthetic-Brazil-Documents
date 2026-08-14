"""Grava os artefatos de uma amostra na árvore dataset/ (PLANO_GERADOR.md
secao 2.2). O `metadata/*.meta.json` é escrito por ÚLTIMO e atomicamente
(escreve em .tmp, depois os.rename) — é o único critério de "amostra
pronta" usado pelo checkpoint/resume do batch driver (secao 3.2/15)."""

import json
import os
from pathlib import Path

from export.sharding import shard_dir


def _atomic_write_bytes(path: Path, data: bytes):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def _atomic_write_text(path: Path, text: str):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf8")
    os.replace(tmp, path)


def sample_paths(out_dir: Path, doctype: str, index: int, sid: str) -> dict:
    shard = shard_dir(index)
    base = out_dir / doctype
    return {
        "xml": base / "xml" / shard / f"{sid}.xml",
        "pdf": base / "pdfs" / shard / f"{sid}.pdf",
        "image": base / "images" / shard / f"{sid}.png",
        "image_geo": base / "images_geo" / shard / f"{sid}.png",
        "label": base / "labels" / shard / f"{sid}.json",
        "meta": base / "metadata" / shard / f"{sid}.meta.json",
    }


def is_sample_done(out_dir: Path, doctype: str, index: int, sid: str) -> bool:
    """Critério único de checkpoint/resume (PLANO_GERADOR.md secao 3.2/15):
    o meta.json só existe se TODA a amostra foi exportada com sucesso."""
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
    image_clean,
    image_geo,
    label: dict,
    meta: dict,
):
    paths = sample_paths(out_dir, doctype, index, sid)
    for p in paths.values():
        p.parent.mkdir(parents=True, exist_ok=True)

    _atomic_write_text(paths["xml"], xml_str)
    _atomic_write_bytes(paths["pdf"], pdf_bytes)
    image_clean.save(paths["image"], format="PNG")
    if image_geo is not None:
        image_geo.save(paths["image_geo"], format="PNG")
    _atomic_write_text(paths["label"], json.dumps(label, ensure_ascii=False, indent=2))
    # meta.json por ÚLTIMO — é o sinal de "amostra pronta" (ver is_sample_done)
    _atomic_write_text(paths["meta"], json.dumps(meta, ensure_ascii=False, indent=2))

    return paths
