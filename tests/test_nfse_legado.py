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
