import json
from decimal import Decimal
from xml.etree import ElementTree as ET

from nfselib.ginfes.bindings.servico_enviar_lote_rps_envio_v03 import (
    EnviarLoteRpsEnvio,
)
from xsdata.formats.dataclass.parsers import XmlParser

from generator.nfse_legado import generate_nfse_legado

_NS = "{http://www.ginfes.com.br/tipos_v03.xsd}"


def _parse(xml_str):
    parser = XmlParser()
    return parser.from_string(xml_str, EnviarLoteRpsEnvio)


def test_generate_nfse_legado_is_well_formed_xml():
    xml_str, _ = generate_nfse_legado(seed=1)
    ET.fromstring(xml_str)  # não lança em XML malformado


def test_generate_nfse_legado_is_deterministic_per_seed():
    xml_a, values_a = generate_nfse_legado(seed=7)
    xml_b, values_b = generate_nfse_legado(seed=7)
    assert xml_a == xml_b
    assert values_a == values_b


def test_generate_nfse_legado_differs_across_seeds():
    xml_a, _ = generate_nfse_legado(seed=1)
    xml_b, _ = generate_nfse_legado(seed=2)
    assert xml_a != xml_b


def test_generate_nfse_legado_conforms_to_ginfes_binding():
    xml_str, field_values = generate_nfse_legado(seed=3)
    envio = _parse(xml_str)

    rps = envio.LoteRps.ListaRps.Rps[0]
    inf_rps = rps.InfRps

    assert envio.LoteRps.Cnpj == field_values["cnpj_prestador"]
    assert envio.LoteRps.InscricaoMunicipal == field_values["inscricao_municipal"]
    assert envio.LoteRps.QuantidadeRps == 1
    assert len(envio.LoteRps.ListaRps.Rps) == 1

    assert inf_rps.IdentificacaoRps.Numero == int(field_values["numero_rps"])
    assert inf_rps.Prestador.Cnpj == field_values["cnpj_prestador"]
    assert inf_rps.Tomador.RazaoSocial == field_values["razao_social_tomador"]
    assert inf_rps.Servico.ItemListaServico == field_values["item_lista_servico"]
    assert inf_rps.Servico.Discriminacao == field_values["discriminacao"]
    v_serv_esperado = Decimal(f"{field_values['v_serv']:.2f}")
    v_iss_esperado = Decimal(f"{field_values['v_iss']:.2f}")
    assert inf_rps.Servico.Valores.ValorServicos == v_serv_esperado
    assert inf_rps.Servico.Valores.ValorIss == v_iss_esperado


def test_generate_nfse_legado_tomador_documento_tem_11_ou_14_digitos():
    for seed in range(30):
        _, field_values = generate_nfse_legado(seed=seed)
        doc = field_values["cpf_cnpj_tomador"]
        assert len(doc) in (11, 14)


def test_generate_nfse_legado_covers_pessoa_fisica_e_juridica():
    doc_lengths = {
        len(generate_nfse_legado(seed=seed)[1]["cpf_cnpj_tomador"])
        for seed in range(30)
    }
    assert doc_lengths == {11, 14}


def test_generate_nfse_legado_prestador_cnpj_tem_14_digitos():
    _, field_values = generate_nfse_legado(seed=5)
    assert len(field_values["cnpj_prestador"]) == 14


# --- renderizador PDF, labels e pipeline ------------------------------------

from pipeline.registry import DOCTYPES  # noqa: E402


def test_renderer_produces_single_page_pdf():
    spec = DOCTYPES["nfse_legado"]
    xml_str, _, render_kwargs = spec.generate(4)
    pdf = bytes(spec.render(xml_str, render_kwargs).output())
    assert pdf.startswith(b"%PDF")
    import fitz

    doc = fitz.open(stream=pdf, filetype="pdf")
    assert doc.page_count == 1
    assert "SEM VALIDADE FISCAL" not in doc[0].get_text()  # sem avisos de validade


def test_flatten_matches_pdf_text_for_every_field():
    import fitz

    from generator.labels.layout import flatten_nfse_legado_fields

    spec = DOCTYPES["nfse_legado"]
    xml_str, field_values, render_kwargs = spec.generate(4, city_layout="ginfes")
    render_kwargs = {**render_kwargs, "city_layout": "ginfes"}
    pdf = bytes(spec.render(xml_str, render_kwargs).output())
    text = fitz.open(stream=pdf, filetype="pdf")[0].get_text()
    for field_id, value in flatten_nfse_legado_fields(field_values).items():
        assert value in text, f"{field_id}={value!r} não aparece no PDF"


def test_cep_keeps_leading_zero():
    from renderers.nfse_legado import format_cep_nfse

    assert format_cep_nfse("1310100") == "01310-100"
    assert format_cep_nfse(36880000) == "36880-000"


def test_pipeline_nfse_legado_fully_matched(tmp_path):
    from pipeline.single import generate_one

    row = generate_one("nfse_legado", "train", 0, 9, tmp_path, dpi_options=(110,), force=True)
    # capitais usam moldes de notas reais (nem todo campo do XML é impresso): match alto, não total
    assert row and row["match_rate"] >= 0.6 and row["n_pages"] == 1
    assert row["has_html"] is False
    label = json.loads(next((tmp_path / "nfse_legado" / "labels").rglob("*.json")).read_text())
    assert label["doc_type"] == "NFSE_LEGADO"
    assert label["kie"]["provider"]["tax_id_type"] in ("cnpj", "cnpj_alnum")
    assert label["kie"]["service"]["code"]["value"]


def test_pipeline_nfse_legado_html_derived(tmp_path):
    from pipeline.single import generate_one

    row = generate_one("nfse_legado", "train", 1, 9, tmp_path, dpi_options=(110,), html=True, force=True)
    assert row["has_html"] and row["text_fidelity"] >= 0.95
    assert list((tmp_path / "nfse_legado" / "md_visible").rglob("*.md"))
