from pathlib import Path

import lxml.html
import pytest

from htmlgen.convert import to_clean_html, to_markdown
from htmlgen.fidelity import text_fidelity
from htmlgen.pdf2html import pdf_to_html
from htmlgen.registry import PDF_DERIVED, html_specs
from pipeline.registry import DOCTYPES
from pipeline.single import generate_one

NEEDS_CHROMIUM = pytest.mark.skipif(not Path("/opt/pw-browsers").exists(), reason="Chromium indisponível")


def _lib_pdf(doctype, seed=5):
    spec = DOCTYPES[doctype]
    xml, fv, kw = spec.generate(seed)
    return xml, fv, bytes(spec.render(xml, kw).output())


@pytest.mark.parametrize("doctype", PDF_DERIVED)
def test_html_text_matches_pdf_and_has_structure(doctype):
    _xml, _fv, pdf = _lib_pdf(doctype)
    full = pdf_to_html(pdf, doctype)
    clean = to_clean_html(full)
    assert text_fidelity(clean, pdf) >= 0.98
    doc = lxml.html.document_fromstring(clean)
    assert doc.xpath("//article/section")
    assert doc.xpath("//dl/div/dt") or doc.xpath("//table")  # campos ou tabelas, não só parágrafos
    # decoração (SVG de linhas, estilo, posições) não vaza para o alvo
    assert "<svg" not in clean and "style=" not in clean and "class=" not in clean
    assert to_markdown(full, "table").strip()


def test_dacte_html_keeps_key_blocks_and_watermark():
    _xml, _fv, pdf = _lib_pdf("dacte")
    clean = to_clean_html(pdf_to_html(pdf, "dacte"))
    for label in ("CHAVE DE ACESSO", "TIPO DO SERVIÇO", "REMETENTE", "DESTINATÁRIO", "OBSERVAÇÕES"):
        assert label in clean
    assert 'data-kind="watermark"' in clean and "SEM VALOR FISCAL" in clean
    assert 'alt="QR Code"' in clean and 'alt="Código de barras"' in clean


def test_specs_registered_for_every_doctype():
    assert set(html_specs()) == {"danfe", *PDF_DERIVED}
    assert "nfse_legado" in PDF_DERIVED


def test_pdf_derived_spec_requires_lib_pdf():
    with pytest.raises(ValueError):
        html_specs()["dacte"].render("<x/>", {}, 1, None, lib_pdf=None, need_pdf=False)


@NEEDS_CHROMIUM
@pytest.mark.parametrize("doctype", ["dacte", "danfse"])
def test_pipeline_image_source_html(tmp_path, doctype):
    row = generate_one(doctype, "train", 0, 9, tmp_path, dpi_options=(110,), html=True,
                       image_source="html", force=True)
    assert row and row["has_html"] and row["text_fidelity"] >= 0.95
    assert list((tmp_path / doctype / "html_visible").rglob("*.html"))
