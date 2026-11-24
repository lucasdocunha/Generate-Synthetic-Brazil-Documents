import random
from pathlib import Path

import pytest
from PIL import Image

from augmentation.context import CONTEXT_FNS
from augmentation.stamps import compose_document_artifacts
from pipeline.registry import DOCTYPES
from pipeline.single import generate_one

NEEDS_CHROMIUM = pytest.mark.skipif(not Path("/opt/pw-browsers").exists(), reason="Chromium indisponível")


@pytest.mark.parametrize("doctype", list(DOCTYPES))
def test_context_is_complete_for_every_doctype(doctype):
    spec = DOCTYPES[doctype]
    _xml, fv, _ = spec.generate(11)
    ctx = spec.augment_context(fv)
    assert ctx["cnpj"] and ctx["name"] and ctx["date_br"] and ctx["cnpj_field_id"]
    assert ctx["address"]["municipality_name"]
    # o emitente do contexto é o do documento, não o "posto" fictício padrão
    assert ctx["name"] != "AUTO POSTO BRASIL LTDA"


def test_cce_has_no_amount_so_no_pos_receipt():
    spec = DOCTYPES["dacce"]
    _xml, fv, _ = spec.generate(5)
    ctx = spec.augment_context(fv)
    assert ctx["amount"] is None
    img = Image.new("RGB", (1240, 1754), "white")
    for seed in range(12):
        _, objs = compose_document_artifacts(
            img, fv, {"w": 210, "h": 297}, random.Random(seed), preset="pos_overlay", context=ctx
        )
        assert all(o["type"] != "pos_receipt" for o in objs)


def test_signature_leaves_header_when_layout_has_no_receipt():
    spec = DOCTYPES["danfse"]
    _xml, fv, _ = spec.generate(3)
    ctx = spec.augment_context(fv)
    assert ctx["has_receipt"] is False
    img = Image.new("RGB", (1240, 1754), "white")
    for seed in range(15):
        _, objs = compose_document_artifacts(
            img, fv, {"w": 210, "h": 297}, random.Random(seed), preset="signature_and_scratches",
            context=ctx, label={"elements": []},
        )
        for o in objs:
            if o["type"] == "signature":
                assert o["bbox"]["y"] > 0.7 * 297  # não cai no cabeçalho


def test_context_functions_cover_all_registered_doctypes():
    assert set(DOCTYPES) <= set(CONTEXT_FNS)


@NEEDS_CHROMIUM
def test_pipeline_html_writes_all_artifacts(tmp_path):
    row = generate_one("danfe", "train", 0, 7, tmp_path, dpi_options=(110,), html=True, force=True)
    assert row and row["has_html"] and row["text_fidelity"] >= 0.9
    base = tmp_path / "danfe"
    for sub in ("html", "html_clean", "md", "html_visible", "md_visible", "images_aug", "labels", "metadata"):
        assert list((base / sub).rglob("*.*")), sub
    assert list((base / "images").rglob("*_p1.png"))


def test_pipeline_without_html_flag_skips_html_artifacts(tmp_path):
    row = generate_one("dacce", "train", 0, 7, tmp_path, dpi_options=(110,), html=False, force=True)
    assert row and row["has_html"] is False
    assert not (tmp_path / "dacce" / "html_clean").exists()
