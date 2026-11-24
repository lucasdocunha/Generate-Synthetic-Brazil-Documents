"""Fluxo de geração de UMA amostra, ponta-a-ponta (PLANO_GERADOR.md secao 3.1).

seed -> field_values/xml -> render PDF (renderers/) [+ HTML/Markdown com --html]
-> rasterize -> labels (kie via casamento pos-renderizacao, layout.py)
-> augment (degradação) [-> html_visible] -> validate -> export.
"""

import hashlib
import json
import tempfile
import traceback
from pathlib import Path

from augmentation.pipeline import augment_document, augment_geometric_variant
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
    gen_opts: dict = None,
    html: bool = False,
    image_source: str = "lib_pdf",
):
    out_dir = Path(out_dir)
    sid = sample_id(doctype, split, index)

    if not force and is_sample_done(out_dir, doctype, index, sid):
        return _read_existing_manifest_row(out_dir, doctype, index, sid)

    seed = derive_seed(run_seed, doctype, split, index)
    try:
        return _generate_one_inner(
            doctype, split, index, sid, seed, out_dir, dpi_options, generate_geometric_variant,
            gen_opts or {}, html, image_source,
        )
    except Exception:
        if _retry:
            _log_failure(out_dir, doctype, split, index, seed, traceback.format_exc())
            return None
        # 1 nova tentativa com seed derivado diferente (PLANO_GERADOR.md secao 3.2)
        return generate_one(
            doctype, split, index, run_seed + 1_000_000_007, out_dir, dpi_options,
            generate_geometric_variant, force=True, _retry=True, gen_opts=gen_opts,
            html=html, image_source=image_source,
        )


def _generate_one_inner(doctype, split, index, sid, seed, out_dir, dpi_options, gen_geo, gen_opts,
                        html=False, image_source="lib_pdf"):
    import random

    from generator.labels.layout import build_label

    rng = random.Random(seed)
    spec = DOCTYPES[doctype]

    xml_str, field_values, render_kwargs = spec.generate(seed, **gen_opts)
    field_errors = validate_field_values(doctype, field_values)  # log-only, ver validation/schemas.py

    # PDF real da lib (sempre): é a imagem padrão e a base das specs derivadas de PDF
    lib_pdf_bytes = bytes(spec.render(xml_str, render_kwargs).output())

    # --- HTML (opcional): um Chromium por processo ---------------------------
    html_spec = spec.html_spec() if html else None
    html_res = None
    if html_spec is not None:
        from htmlgen.render import get_renderer

        html_res = html_spec.render(
            xml_str, field_values, seed, get_renderer(), lib_pdf=lib_pdf_bytes,
            need_pdf=(image_source == "html"),
        )
    if image_source == "html" and html_res is None:
        raise ValueError(f"image_source='html' exige HTML disponível para '{doctype}'")
    pdf_bytes = html_res.pdf_bytes if image_source == "html" else lib_pdf_bytes

    with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp:
        tmp.write(pdf_bytes)
        tmp.flush()

        dpi = rng.choice(list(dpi_options))
        images = rasterize(tmp.name, dpi=dpi)

        source = {
            "xml_path": f"xml/{index // 10_000:04d}/{sid}.xml",
            "pdf_path": f"pdfs/{index // 10_000:04d}/{sid}.pdf",
            "fixture_template": field_values.get("_template_id", "tpl_001"),
            "generation_seed": seed,
            "image_source": image_source,
        }
        if html_res is not None:
            sh = f"{index // 10_000:04d}"
            source.update(
                html_path=f"html_clean/{sh}/{sid}.html", md_path=f"md/{sh}/{sid}.md",
                html_visible_path=f"html_visible/{sh}/{sid}.html",
            )
        label = build_label(
            tmp.name, field_values, doc_type=doctype.upper(), doc_id=sid, source=source,
            flatten_fn=spec.flatten_fn, has_vector_barcode=spec.has_vector_barcode,
        )
        label["kie"] = spec.kie_builder(field_values, label.pop("field_id_to_element"))
        label["dpi"] = dpi

        image_aug, label, aug_params = augment_document(
            images[0], label, field_values, seed=seed, context=spec.augment_context(field_values)
        )
        image_geo = None
        if gen_geo:
            image_geo, geo_params = augment_geometric_variant(images[0], seed=seed)

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
        "image_source": image_source,
        "n_pages": len(images),
        "field_errors": field_errors,
        "label_schema_ok": label_schema_ok,
        "augmentation": aug_params,
    }
    # Variante estrutural (quando o gerador expõe): perfil sorteado, config do
    # renderer e formato de CNPJ por parte — para estratificar splits/avaliação.
    for key in ("_template_id", "_profile", "_render", "_doc_formats"):
        if key in field_values:
            meta[key.lstrip("_")] = field_values[key]

    texts = None
    text_fidelity = None
    if html_res is not None:
        from htmlgen.convert import to_clean_html, to_markdown
        from htmlgen.fidelity import text_fidelity as _fid
        from htmlgen.occlusion import apply_degradation

        clean = to_clean_html(html_res.html_full)
        vis_full, occ = apply_degradation(html_res.html_full, label)
        text_fidelity = _fid(clean, pdf_bytes)
        texts = {
            "html": html_res.html_full,
            "html_clean": clean,
            "md": to_markdown(html_res.html_full, html_res.md_style),
            "html_visible": to_clean_html(vis_full),
            "md_visible": to_markdown(vis_full, html_res.md_style),
        }
        meta["html"] = {
            "n_pages_html": html_res.n_pages,
            "text_fidelity": text_fidelity,
            "style": html_res.style,
            "occlusion": occ,
        }

    write_sample(out_dir, doctype, index, sid, xml_str, pdf_bytes, images, image_aug, image_geo,
                 label, meta, texts)

    return {
        "doc_id": sid,
        "doctype": doctype,
        "split": split,
        "seed": seed,
        "match_rate": label["extraction_stats"]["match_rate"],
        "n_pages": len(label["pages"]),
        "has_html": html_res is not None,
        "text_fidelity": text_fidelity,
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
            "has_html": "html" in meta,
            "text_fidelity": meta.get("html", {}).get("text_fidelity"),
        }
    except (OSError, json.JSONDecodeError):
        return None


def _log_failure(out_dir: Path, doctype: str, split: str, index: int, seed: int, tb: str):
    log_path = Path(out_dir) / doctype / ".failed_samples.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a", encoding="utf8") as f:
        f.write(json.dumps({"split": split, "index": index, "seed": seed, "traceback": tb}) + "\n")
