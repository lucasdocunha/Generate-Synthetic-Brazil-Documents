import xml.etree.ElementTree as ET

import pytest

from brazilfiscalreport.danfe import Danfe
from generator.danfe import generate_danfe, render_kwargs
from generator.labels.kie import build_kie_danfe
from validation.schemas import validate_field_values

NS = "{http://www.portalfiscal.inf.br/nfe}"


def _gen(seed=1, **overrides):
    xml, fv = generate_danfe(seed=seed, profile_overrides=overrides)
    return ET.fromstring(xml), xml, fv


def _render(xml, fv):
    pdf = Danfe(xml=xml, **render_kwargs(fv))
    assert len(bytes(pdf.output())) > 1000
    return pdf


def _has(root, path):
    return root.find(".//" + "/".join(NS + p for p in path.split("/"))) is not None


@pytest.mark.parametrize("seed", range(25))
def test_amostras_aleatorias_renderizam_e_sao_consistentes(seed):
    _, xml, fv = _gen(seed)
    assert validate_field_values("danfe", fv) == []
    _render(xml, fv)


@pytest.mark.parametrize(
    "regime,crt,grupo",
    [
        ("normal", "3", "CST"),
        ("simples", "1", "CSOSN"),
        ("mei", "4", "CSOSN"),
    ],
)
def test_regime_tributario(regime, crt, grupo):
    root, xml, fv = _gen(3, regime=regime, n_items=6, issqn=False)
    assert root.find(f".//{NS}emit/{NS}CRT").text == crt
    for icms in root.iter(f"{NS}ICMS"):
        assert icms[0].find(f"{NS}{grupo}") is not None
    if regime != "normal":
        assert not _has(root, "IPI")
    _render(xml, fv)


@pytest.mark.parametrize(
    "flag,path",
    [
        ("transporta", "transp/transporta"),
        ("cobr", "cobr/dup"),
        ("retirada", "retirada"),
        ("entrega", "entrega"),
        ("ibs_cbs", "IBSCBSTot"),
        ("issqn", "ISSQNtot"),
    ],
)
def test_blocos_opcionais_presentes_e_ausentes(flag, path):
    on, xml_on, fv_on = _gen(5, **{flag: True})
    off, xml_off, fv_off = _gen(5, **{flag: False})
    assert _has(on, path)
    assert not _has(off, path)
    for xml, fv in ((xml_on, fv_on), (xml_off, fv_off)):
        assert validate_field_values("danfe", fv) == []
        _render(xml, fv)


def test_destinatario_pj_vs_pf():
    pj, _, fv_pj = _gen(8, dest_pj=True)
    pf, _, fv_pf = _gen(8, dest_pj=False)
    assert (
        pj.find(f".//{NS}dest/{NS}CNPJ") is not None
        and pj.find(f".//{NS}dest/{NS}CPF") is None
    )
    assert (
        pf.find(f".//{NS}dest/{NS}CPF") is not None
        and pf.find(f".//{NS}dest/{NS}CNPJ") is None
    )
    assert fv_pj["dest_doc_type"] == "cnpj" and fv_pf["dest_doc_type"] == "cpf"


def test_nfeproc_e_paisagem():
    root, xml, fv = _gen(11, nfe_proc=True, landscape=True)
    assert root.tag == f"{NS}nfeProc"
    assert root.find(f"{NS}protNFe/{NS}infProt/{NS}tpAmb").text == "2"
    assert root.find(f".//{NS}ide/{NS}tpImp").text == "2"
    assert _render(xml, fv).cur_orientation.value == "L"


def test_cnpj_alfanumerico_propaga_para_chave_e_kie():
    xml, fv = generate_danfe(
        seed=2, cnpj_alnum_ratio=1.0, profile_overrides={"dest_pj": True}
    )
    chave = fv["chave_acesso"]
    assert any(c.isalpha() for c in fv["emit_cnpj"])
    assert chave[6:20] == fv["emit_cnpj"]
    assert fv["_doc_formats"]["emit"] == "cnpj_alnum"
    kie = build_kie_danfe(fv)
    assert kie["issuer"]["tax_id_type"] == "cnpj_alnum"
    assert kie["recipient"]["tax_id_type"] == "cnpj_alnum"
    _render(xml, fv)


def test_ratio_zero_so_numerico():
    for s in range(20):
        _, fv = generate_danfe(seed=s, cnpj_alnum_ratio=0.0)
        assert set(fv["_doc_formats"].values()) <= {"cnpj_numeric", "cpf"}


def test_reprodutivel_por_seed():
    assert generate_danfe(seed=42)[0] == generate_danfe(seed=42)[0]
