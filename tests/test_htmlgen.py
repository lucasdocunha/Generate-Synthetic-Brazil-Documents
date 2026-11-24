import random
from pathlib import Path

import lxml.html
import pytest

from generator.danfe import generate_danfe
from htmlgen.convert import to_clean_html, to_markdown
from htmlgen.models.nfe import fmt_chave, fmt_doc, money, parse_nfe
from htmlgen.specs.danfe import xml_to_html
from htmlgen.styles.danfe import sample_style


def test_formatters():
    assert money("1234.5") == "1.234,50"
    assert fmt_doc("12345678000195") == "12.345.678/0001-95"
    assert fmt_doc("12345678901") == "123.456.789-01"
    assert fmt_chave("1" * 8) == "1111 1111"


@pytest.fixture(scope="module")
def sample():
    xml, _ = generate_danfe(seed=7)
    style = sample_style(random.Random(7))
    return xml, style, xml_to_html(xml, style, seed=7)


def test_parse_matches_xml(sample):
    xml, style, _ = sample
    d = parse_nfe(xml)
    assert len(d["products"]) == xml.count("<det ")
    assert len(d["chave_raw"]) == 44


def test_clean_html_has_no_style_layer(sample):
    _, _, html = sample
    clean = to_clean_html(html)
    assert "<style" not in clean and "class=" not in clean and "style=" not in clean
    assert "data:image" not in clean
    assert "<dl>" in clean and "<table>" in clean


def test_markdown_has_same_text_as_html(sample):
    _, style, html = sample
    clean = to_clean_html(html)
    md = to_markdown(html, style.md_style)
    d = lxml.html.document_fromstring(clean)
    cells = d.xpath("//table[thead]//tbody/tr[1]/td")
    for td in (cells[0], cells[2]):  # código e NCM: texto simples, sem <br>
        assert td.text_content().strip() in md


def test_style_is_deterministic():
    assert sample_style(random.Random(1)) == sample_style(random.Random(1))


@pytest.mark.skipif(not Path("/opt/pw-browsers").exists(), reason="Chromium indisponível")
def test_html_spec_end_to_end():
    from htmlgen.fidelity import text_fidelity
    from htmlgen.render import get_renderer
    from htmlgen.registry import html_specs

    xml, fv = generate_danfe(seed=123)
    res = html_specs()["danfe"].render(xml, fv, 123, get_renderer())
    assert res.n_pages >= 1 and res.pdf_bytes[:4] == b"%PDF"
    assert text_fidelity(to_clean_html(res.html_full), res.pdf_bytes) >= 0.95
