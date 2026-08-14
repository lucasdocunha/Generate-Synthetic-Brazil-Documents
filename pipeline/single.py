"""Fluxo de geração de UMA amostra, ponta-a-ponta (PLANO_GERADOR.md secao 3.1).

seed -> field_values/xml -> render (record_fields indisponivel, ver
PLANO_GERADOR.md "Questões em aberto" #1) -> rasterize -> augment -> labels
(kie via casamento pos-renderizacao, layout.py) -> validate -> export.
"""

import hashlib
import json
import tempfile
import traceback
from pathlib import Path

from augmentation.pipeline import augment_clean, augment_geometric_variant
from export.sharding import sample_id
from export.writer import is_sample_done, write_sample
from pipeline.registry import DOCTYPES
from rasterization.raster import rasterize
from validation.schemas import LabelRecord, validate_field_values


def derive_seed(run_seed: int, doctype: str, split: str, index: int) -> int:
    """Seed determinístico por amostra — independente de ordem/worker
    (PLANO_GERADOR.md secao 3.2). Mascarado em 63 bits para caber num int64
    assinado (o manifesto Parquet grava `seed` como inteiro)."""
    h = hashlib.sha256(f"{run_seed}:{doctype}:{split}:{index}".encode()).digest()
    return int.from_bytes(h[:8], byteorder="big") & 0x7FFFFFFFFFFFFFFF


def generate_one(
    doctype: str,
    split: str,
    index: int,
    run_seed: int,
    out_dir: Path,
    dpi_options=(150, 200, 300),
    generate_geometric_variant: bool = True,
    force: bool = False,
    _retry: bool = False,
):
    out_dir = Path(out_dir)
    sid = sample_id(doctype, split, index)

    if not force and is_sample_done(out_dir, doctype, index, sid):
        return _read_existing_manifest_row(out_dir, doctype, index, sid)

    seed = derive_seed(run_seed, doctype, split, index)
    try:
        return _generate_one_inner(doctype, split, index, sid, seed, out_dir, dpi_options, generate_geometric_variant)
    except Exception:
        if _retry:
            _log_failure(out_dir, doctype, split, index, seed, traceback.format_exc())
            return None
        # 1 nova tentativa com seed derivado diferente (PLANO_GERADOR.md secao 3.2)
        return generate_one(
            doctype, split, index, run_seed + 1_000_000_007, out_dir, dpi_options,
            generate_geometric_variant, force=True, _retry=True,
        )


def _generate_one_inner(doctype, split, index, sid, seed, out_dir, dpi_options, gen_geo):
    import random

    rng = random.Random(seed)
    spec = DOCTYPES[doctype]

    xml_str, field_values, render_kwargs = spec.generate(seed)
    field_errors = validate_field_values(doctype, field_values)  # log-only, ver validation/schemas.py

    pdf_obj = spec.render(xml_str, render_kwargs)
    pdf_bytes = bytes(pdf_obj.output())

    with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp:
        tmp.write(pdf_bytes)
        tmp.flush()

        dpi = rng.choice(list(dpi_options))
        images = rasterize(tmp.name, dpi=dpi)
        image_clean, aug_params = augment_clean(images[0], seed=seed)
        image_geo = None
        if gen_geo:
            image_geo, geo_params = augment_geometric_variant(images[0], seed=seed)

        from generator.labels.layout import build_label

        source = {
            "xml_path": f"xml/{index // 10_000:04d}/{sid}.xml",
            "pdf_path": f"pdfs/{index // 10_000:04d}/{sid}.pdf",
            "fixture_template": "tpl_001",
            "generation_seed": seed,
        }
        label = build_label(
            tmp.name, field_values, doc_type=doctype.upper(), doc_id=sid, source=source,
            flatten_fn=spec.flatten_fn, has_vector_barcode=spec.has_vector_barcode,
        )
        label["kie"] = spec.kie_builder(field_values, label.pop("field_id_to_element"))
        label["dpi"] = dpi

    try:
        LabelRecord(**label)
        label_schema_ok = True
    except Exception as e:  # noqa: BLE001 - queremos logar, nao travar o lote
        label_schema_ok = False
        field_errors.append(f"label schema: {e}")

    meta = {
        "seed": seed,
        "doctype": doctype,
        "split": split,
        "index": index,
        "dpi": dpi,
        "field_errors": field_errors,
        "label_schema_ok": label_schema_ok,
    }

    write_sample(out_dir, doctype, index, sid, xml_str, pdf_bytes, image_clean, image_geo, label, meta)

    return {
        "doc_id": sid,
        "doctype": doctype,
        "split": split,
        "seed": seed,
        "match_rate": label["extraction_stats"]["match_rate"],
        "n_pages": len(label["pages"]),
    }


def _read_existing_manifest_row(out_dir, doctype, index, sid):
    from export.writer import sample_paths

    paths = sample_paths(out_dir, doctype, index, sid)
    try:
        label = json.loads(paths["label"].read_text(encoding="utf8"))
        meta = json.loads(paths["meta"].read_text(encoding="utf8"))
        return {
            "doc_id": sid,
            "doctype": doctype,
            "split": meta.get("split"),
            "seed": meta.get("seed"),
            "match_rate": label.get("extraction_stats", {}).get("match_rate", 0.0),
            "n_pages": len(label.get("pages", [])),
        }
    except (OSError, json.JSONDecodeError):
        return None


def _log_failure(out_dir: Path, doctype: str, split: str, index: int, seed: int, tb: str):
    log_path = Path(out_dir) / doctype / ".failed_samples.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a", encoding="utf8") as f:
        f.write(json.dumps({"split": split, "index": index, "seed": seed, "traceback": tb}) + "\n")
