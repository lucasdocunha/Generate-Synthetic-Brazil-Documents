"""Testes para as novas funcionalidades:
1. CNPJs alfanuméricos em todos os tipos (dacte, damdfe, danfse, dacce, nfe_portal);
2. Logos procedurais (logo_factory);
3. Variações de layout de DANFE por ERP, orientação paisagem e destinatário real;
4. Consulta Web do Portal da NF-e (classic_fazenda e modern_svrs);
5. Carimbos, assinaturas, comprovantes POS, scanner P&B e rotação com reprojeção de bboxes.
"""

from pathlib import Path
import random

from PIL import Image

from augmentation.pipeline import augment_document
from renderers.danfe import Danfe
from renderers.portal_nfe import PortalNfe
from generator.branding.logo_factory import generate_company_logo
from generator.dacce import generate_dacce
from generator.dacte import generate_dacte
from generator.damdfe import generate_damdfe
from generator.danfe import generate_danfe, render_kwargs as danfe_render_kwargs
from generator.danfse import generate_danfse
from generator.fake_data import is_alnum_cnpj
from generator.labels import kie, layout
from generator.portal_nfe import generate_portal_nfe, render_kwargs as portal_render_kwargs
from pipeline.single import generate_one
from validation.schemas import LabelRecord, validate_field_values


def test_alnum_cnpj_all_doctypes():
    xml_ct, fv_ct = generate_dacte(seed=10, cnpj_alnum_ratio=1.0)
    assert is_alnum_cnpj(fv_ct["emit"]["cnpj"])
    assert fv_ct["_doc_formats"]["emit"] == "cnpj_alnum"
    assert not validate_field_values("dacte", fv_ct)
    assert kie.build_kie_dacte(fv_ct)["issuer"]["tax_id_type"] == "cnpj_alnum"

    xml_md, fv_md = generate_damdfe(seed=11, cnpj_alnum_ratio=1.0)
    assert is_alnum_cnpj(fv_md["emit_cnpj"])
    assert fv_md["_doc_formats"]["emit"] == "cnpj_alnum"
    assert not validate_field_values("damdfe", fv_md)
    assert kie.build_kie_damdfe(fv_md)["issuer"]["tax_id_type"] == "cnpj_alnum"

    xml_nfse, fv_nfse = generate_danfse(seed=12, cnpj_alnum_ratio=1.0)
    assert is_alnum_cnpj(fv_nfse["emit_cnpj"])
    assert fv_nfse["_doc_formats"]["emit"] == "cnpj_alnum"
    assert not validate_field_values("danfse", fv_nfse)
    assert kie.build_kie_danfse(fv_nfse)["provider"]["tax_id_type"] == "cnpj_alnum"

    xml_cc, emit_cc, fv_cc = generate_dacce(seed=13, cnpj_alnum_ratio=1.0)
    assert is_alnum_cnpj(fv_cc["autor_cnpj"])
    assert is_alnum_cnpj(fv_cc["dest_cnpj"])
    assert not validate_field_values("dacce", fv_cc)
    assert kie.build_kie_dacce(fv_cc)["event"]["author_tax_id_type"] == "cnpj_alnum"


def test_logo_factory_styles():
    rng = random.Random(42)
    for style in ("badge_seal", "modern_corporate", "fuel_shield", "minimal_monogram"):
        buf = generate_company_logo(rng, "Comércio Amor em Grãos LTDA", style=style)
        img = Image.open(buf)
        assert img.size == (360, 220)


def test_danfe_erp_presets_and_real_dest(tmp_path):
    for idx, erp in enumerate(
        ("linx_autosystem", "xpert", "galago", "minimal_open", "classic_landscape")
    ):
        xml_str, fv = generate_danfe(
            seed=100 + idx,
            num_items=3,
            profile_overrides={"erp_style": erp, "has_logo": True},
            cnpj_alnum_ratio=1.0,
        )
        pdf = Danfe(xml=xml_str, **danfe_render_kwargs(fv))
        out_pdf = tmp_path / f"danfe_{erp}.pdf"
        pdf.output(str(out_pdf))
        lbl = layout.build_label(
            out_pdf,
            fv,
            doc_type="DANFE",
            doc_id=f"test_{erp}",
            source={},
            flatten_fn=layout.flatten_danfe_fields,
            has_vector_barcode=True,
        )
        # Destinatário real deve aparecer no texto extraído do PDF
        assert fv["dest_xNome"] in lbl["ocr"]["full_text"]


def test_portal_nfe_variants(tmp_path):
    for idx, variant in enumerate(("classic_fazenda", "modern_svrs")):
        xml_str, fv = generate_portal_nfe(seed=200 + idx, variant=variant, cnpj_alnum_ratio=1.0)
        pdf = PortalNfe(xml=xml_str, **portal_render_kwargs(fv))
        out_pdf = tmp_path / f"portal_{variant}.pdf"
        pdf.output(str(out_pdf))
        lbl = layout.build_label(
            out_pdf,
            fv,
            doc_type="NFE_PORTAL",
            doc_id=f"portal_{idx}",
            source={},
            flatten_fn=layout.flatten_portal_nfe_fields,
            has_vector_barcode=False,
        )
        lbl["kie"] = kie.build_kie_danfe(fv, lbl.pop("field_id_to_element"))
        rec = LabelRecord(**lbl)
        assert rec.doc_type == "NFE_PORTAL"
        assert lbl["extraction_stats"]["match_rate"] >= 0.70


def test_augmentation_artifacts_and_bbox_reprojection(tmp_path):
    row = generate_one("danfe", "train", 0, 77, tmp_path, dpi_options=(150,), force=True)
    assert row is not None
    base_img = Image.new("RGB", (1240, 1754), (255, 255, 255))
    dummy_label = {
        "pages": [{"page_number": 1, "size_mm": {"w": 210.0, "h": 297.0}}],
        "elements": [
            {
                "element_id": "e00001",
                "field_ids": ["emit_cnpj_cpf"],
                "role": "content",
                "page": 1,
                "bbox": {"x": 20.0, "y": 40.0, "w": 50.0, "h": 6.0, "unit": "mm"},
                "text": "12.345.678/0001-99",
            }
        ],
        "layout": {"special_objects": []},
    }
    img_aug, lbl_aug, meta = augment_document(
        base_img,
        dummy_label,
        {"emit_cnpj": "12ABC345000192", "emit_xNome": "POSTO TESTE LTDA", "total_vNF": 350.0},
        seed=99,
        artifact_preset="pos_and_stamp",
        scan_mode="bw_binarized_scan",
        angle_deg=2.5,
    )
    assert meta["boxes_valid"] is True
    assert "obb_points" in lbl_aug["elements"][0]["bbox"]
    types = {o["type"] for o in lbl_aug["layout"]["special_objects"]}
    assert "stamp" in types and "pos_receipt" in types
