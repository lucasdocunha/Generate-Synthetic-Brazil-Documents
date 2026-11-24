"""Adaptador do DANFE (PLANO_GERADOR.md secao 6.4).

Gera um XML de NF-e 4.00 sintético a partir do template MAXIMAL tpl_002:
sorteia um perfil estrutural (`generator/nfe_profile.py`), poda os blocos
ausentes e preenche o resto de forma internamente consistente. Expõe
generate_danfe(seed) -> (xml_str, field_values), o contrato do pipeline.

Eixos de variação (pesos em generator/schemas/danfe.yaml, seção `profiles`):
- regime tributário: normal (CST 00/10/20/40/41/60/90 + IPI tributado ou
  não), Simples Nacional e MEI (CSOSN 101/102/103/300/400/500/900);
- partes opcionais: destinatário PF/PJ, transportadora/veículo/volumes,
  cobrança com duplicatas, retirada, entrega, frete/seguro/outros/desconto;
- extras: itens ANP (<comb>) e ANVISA (<med> + <rastro>), itens de serviço
  (ISSQN + ISSQNtot), IBS/CBS (reforma tributária), infAdProd, infCpl,
  envelope nfeProc/protNFe, nº de itens de cauda longa (multipágina);
- config do renderer (`field_values["_render"]`, convertido em DanfeConfig
  por `render_kwargs`): paisagem, canhoto, fonte, casas decimais etc.

CNPJs (emitente, destinatário PJ, transportadora, retirada/entrega) podem
ser alfanuméricos (IN RFB 2.229/2024) com fração `cnpj_alnum_ratio`; a chave
de acesso herda as letras do CNPJ do emitente (posições 7-20).

Regras anti-validade inalteradas: tpAmb=2 sempre, DVs corrompidos, cUF da
chave = "00" (PLANO_GERADOR.md secao 9).
"""

import datetime
import random
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml
from faker import Faker

from generator import code_tables, fake_data, xml_builder
from generator.nfe_profile import sample_profile

_SCHEMA_PATH = Path(__file__).resolve().parent / "schemas" / "danfe.yaml"
_TEMPLATE_PATH = (
    Path(__file__).resolve().parent
    / "templates"
    / "danfe"
    / "v1"
    / "tpl_002"
    / "source.xml"
)

with open(_SCHEMA_PATH, encoding="utf8") as _f:
    _SCHEMA = yaml.safe_load(_f)

_NS = _SCHEMA["namespace"]
ET.register_namespace("", _NS)

TEMPLATE_ID = "tpl_002"

_NAT_OP = {
    "venda": [
        "Venda",
        "Venda de mercadoria",
        "Venda de produção do estabelecimento",
        "Venda de mercadoria adquirida de terceiros",
    ],
    "outras": [
        "Remessa para conserto",
        "Remessa em bonificação",
        "Devolução de venda",
        "Transferência entre filiais",
    ],
}


def _money(v: float) -> str:
    return f"{v:.2f}"


def _r2(v: float) -> float:
    return round(v + 1e-9, 2)


# --------------------------------------------------------------------------
# Partes (emitente, destinatário, locais, transportadora)
# --------------------------------------------------------------------------


def _party_doc(rng, alnum_ratio, pj: bool):
    if pj:
        doc = fake_data.cnpj(rng, alnum_ratio=alnum_ratio)
        return doc, "cnpj"
    return fake_data.cpf(rng), "cpf"


def _doc_format(doc: str, doc_type: str) -> str:
    if doc_type == "cpf":
        return "cpf"
    return "cnpj_alnum" if fake_data.is_alnum_cnpj(doc) else "cnpj_numeric"


def _set_doc(el, ns, doc, doc_type):
    """Mantém só CNPJ ou CPF num elemento que tem os dois no template."""
    keep, drop = ("CNPJ", "CPF") if doc_type == "cnpj" else ("CPF", "CNPJ")
    target = el.find(f"{{{ns}}}{keep}")
    other = el.find(f"{{{ns}}}{drop}")
    if target is None:
        # template só tem a outra tag: renomeia in-place, preservando a posição
        other.tag = f"{{{ns}}}{keep}"
        target = other
    elif other is not None:
        el.remove(other)
    target.text = doc


def _fill_emit(root, ns, rng, faker, profile, alnum_ratio):
    emit = xml_builder.find_one(root, "infNFe/emit", ns)
    cnpj = fake_data.cnpj(rng, alnum_ratio=alnum_ratio)
    if profile.regime == "mei":
        nome = f"{fake_data.person_name(rng, faker).upper()} {fake_data.cpf(rng)}"
        fantasia = fake_data.company_name(rng, faker)
    else:
        nome = fake_data.company_name(rng, faker)
        fantasia = fake_data.company_name(rng, faker)
    endereco = fake_data.address(rng, faker)
    ie = fake_data.ie_stub(rng)
    fone = fake_data.phone_number(rng, mobile=rng.random() < 0.5)

    xml_builder.set_text(emit, "CNPJ", ns, cnpj)
    xml_builder.set_text(emit, "xNome", ns, nome)
    xml_builder.set_text(emit, "xFant", ns, fantasia)
    xml_builder.set_text(emit, "IE", ns, ie)
    xml_builder.set_text(emit, "CRT", ns, profile.crt)
    _set_address(emit, "enderEmit", ns, endereco)
    xml_builder.set_text(emit, "enderEmit/fone", ns, fone)
    return {
        "emit_cnpj": cnpj,
        "emit_xNome": nome,
        "emit_xFant": fantasia,
        "emit_IE": ie,
        "emit_endereco": endereco,
        "emit_fone": fone,
    }


def _set_address(parent, base, ns, addr):
    prefix = f"{base}/" if base else ""
    xml_builder.set_text(parent, f"{prefix}xLgr", ns, addr["street"])
    xml_builder.set_text(parent, f"{prefix}nro", ns, addr["number"])
    if addr["complement"]:
        xml_builder.set_text(parent, f"{prefix}xCpl", ns, addr["complement"])
    else:
        xml_builder.remove(parent, f"{prefix}xCpl", ns)
    xml_builder.set_text(parent, f"{prefix}xBairro", ns, addr["neighborhood"])
    xml_builder.set_text(parent, f"{prefix}cMun", ns, addr["municipality_code"])
    xml_builder.set_text(parent, f"{prefix}xMun", ns, addr["municipality_name"])
    xml_builder.set_text(parent, f"{prefix}UF", ns, addr["uf"])
    xml_builder.set_text(parent, f"{prefix}CEP", ns, addr["cep"])


def _fill_dest(root, ns, rng, faker, profile, alnum_ratio, emit_uf):
    dest = xml_builder.find_one(root, "infNFe/dest", ns)
    doc, doc_type = _party_doc(rng, alnum_ratio, pj=profile.dest_pj)
    _set_doc(dest, ns, doc, doc_type)

    if doc_type == "cnpj":
        nome = fake_data.company_name(rng, faker)
        ie = fake_data.ie_stub(rng)
        xml_builder.set_text(dest, "indIEDest", ns, "1")
        xml_builder.set_text(dest, "IE", ns, ie)
    else:
        nome = fake_data.person_name(rng, faker)
        ie = ""
        xml_builder.set_text(dest, "indIEDest", ns, "9")
        xml_builder.remove(dest, "IE", ns)

    # ~70% dentro do mesmo estado (operação interna, CFOP 5xxx)
    endereco = fake_data.address(rng, faker)
    if rng.random() < 0.7:
        same_uf = [m for m in fake_data.load_municipios() if m[2] == emit_uf]
        if same_uf:
            cod, mun, uf = rng.choice(same_uf)
            endereco.update(municipality_code=cod, municipality_name=mun, uf=uf)
    fone = fake_data.phone_number(rng, mobile=rng.random() < 0.6)
    _set_address(dest, "enderDest", ns, endereco)
    xml_builder.set_text(dest, "enderDest/fone", ns, fone)
    xml_builder.set_text(dest, "xNome", ns, nome)

    email = fake_data.email(faker) if rng.random() < 0.7 else ""
    if email:
        xml_builder.set_text(dest, "email", ns, email)
    else:
        xml_builder.remove(dest, "email", ns)

    return {
        "dest_doc": doc,
        "dest_doc_type": doc_type,
        "dest_xNome": nome,
        "dest_IE": ie,
        "dest_endereco": endereco,
        "dest_email": email,
        "dest_fone": fone,
    }


def _fill_location(root, ns, rng, faker, tag, alnum_ratio):
    el = xml_builder.find_one(root, f"infNFe/{tag}", ns)
    doc, doc_type = _party_doc(rng, alnum_ratio, pj=rng.random() < 0.85)
    _set_doc(el, ns, doc, doc_type)
    nome = (
        fake_data.company_name(rng, faker)
        if doc_type == "cnpj"
        else fake_data.person_name(rng, faker)
    )
    endereco = fake_data.address(rng, faker)
    fone = fake_data.phone_number(rng, mobile=False)
    ie = fake_data.ie_stub(rng) if doc_type == "cnpj" else ""
    xml_builder.set_text(el, "xNome", ns, nome)
    _set_address(el, "", ns, endereco)
    xml_builder.set_text(el, "fone", ns, fone)
    if ie:
        xml_builder.set_text(el, "IE", ns, ie)
    else:
        xml_builder.remove(el, "IE", ns)
    return {
        "doc": doc,
        "doc_type": doc_type,
        "xNome": nome,
        "endereco": endereco,
        "fone": fone,
        "IE": ie,
    }


def _placa(rng):
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    return (
        "".join(rng.choice(letters) for _ in range(3))
        + str(rng.randint(0, 9))
        + rng.choice(letters)
        + f"{rng.randint(0, 99):02d}"
    )


def _fill_transp(root, ns, rng, faker, profile, alnum_ratio, peso_base):
    transp = xml_builder.find_one(root, "infNFe/transp", ns)
    if not profile.transporta:
        xml_builder.set_text(transp, "modFrete", ns, "9")
        for tag in ("transporta", "veicTransp", "vol"):
            xml_builder.remove(transp, tag, ns)
        return None

    mod_frete = rng.choices(["0", "1", "2"], weights=[0.6, 0.3, 0.1], k=1)[0]
    xml_builder.set_text(transp, "modFrete", ns, mod_frete)

    t = xml_builder.find_one(transp, "transporta", ns)
    doc, doc_type = _party_doc(rng, alnum_ratio, pj=rng.random() < 0.85)
    _set_doc(t, ns, doc, doc_type)
    if doc_type == "cnpj":
        nome = f"Transportes {faker.last_name()} {rng.choice(['LTDA', 'EIRELI', 'S.A.', 'ME'])}"
        ie = fake_data.ie_stub(rng)
        xml_builder.set_text(t, "IE", ns, ie)
    else:
        nome = fake_data.person_name(rng, faker)
        ie = ""
        xml_builder.remove(t, "IE", ns)
    addr = fake_data.address(rng, faker)
    x_ender = f"{addr['street']}, {addr['number']}"
    xml_builder.set_text(t, "xNome", ns, nome)
    xml_builder.set_text(t, "xEnder", ns, x_ender)
    xml_builder.set_text(t, "xMun", ns, addr["municipality_name"])
    xml_builder.set_text(t, "UF", ns, addr["uf"])

    veiculo = None
    if profile.veiculo:
        veiculo = {
            "placa": _placa(rng),
            "UF": addr["uf"],
            "RNTC": f"{rng.randint(0, 99999999):08d}",
        }
        xml_builder.set_text(transp, "veicTransp/placa", ns, veiculo["placa"])
        xml_builder.set_text(transp, "veicTransp/UF", ns, veiculo["UF"])
        xml_builder.set_text(transp, "veicTransp/RNTC", ns, veiculo["RNTC"])
    else:
        xml_builder.remove(transp, "veicTransp", ns)

    peso_l = round(max(0.1, peso_base * rng.uniform(0.8, 1.2)), 3)
    peso_b = round(peso_l * rng.uniform(1.0, 1.15), 3)
    vol = {
        "qVol": str(rng.randint(1, 300)),
        "esp": rng.choice(code_tables.ESPECIES_VOLUME),
        "marca": faker.last_name().upper() if rng.random() < 0.5 else "",
        "nVol": str(rng.randint(1, 9999)) if rng.random() < 0.5 else "",
        "pesoL": f"{peso_l:.3f}",
        "pesoB": f"{peso_b:.3f}",
    }
    for k, v in vol.items():
        if v:
            xml_builder.set_text(transp, f"vol/{k}", ns, v)
        else:
            xml_builder.remove(transp, f"vol/{k}", ns)

    return {
        "modFrete": mod_frete,
        "doc": doc,
        "doc_type": doc_type,
        "xNome": nome,
        "IE": ie,
        "xEnder": x_ender,
        "xMun": addr["municipality_name"],
        "UF": addr["uf"],
        "veiculo": veiculo,
        "vol": vol,
    }


# --------------------------------------------------------------------------
# Itens e impostos
# --------------------------------------------------------------------------


def _pick_category(rng, profile, force_service=False):
    specials = code_tables.SPECIAL_PRODUCT_CATEGORIES
    if force_service or (profile.issqn and rng.random() < 0.4):
        name = rng.choice([k for k, v in specials.items() if v["kind"] == "service"])
        return name, specials[name]
    if profile.special_items and rng.random() < 0.4:
        name = rng.choice(
            [k for k, v in specials.items() if v["kind"] in ("anp", "anvisa")]
        )
        return name, specials[name]
    name = rng.choice(list(code_tables.PRODUCT_CATEGORIES.keys()))
    variants, ncm_prefix, cfop = code_tables.PRODUCT_CATEGORIES[name]
    return name, {
        "variants": variants,
        "ncm_prefix": ncm_prefix,
        "cfop": cfop,
        "unit": rng.choice(code_tables.UNITS),
        "kind": "goods",
    }


def _make_item(rng, profile, interstate, force_service=False):
    name, cat = _pick_category(rng, profile, force_service)
    kind = cat["kind"]
    variante = rng.choice(cat["variants"])
    cfop = cat["cfop"]
    if interstate:
        cfop = "6" + cfop[1:]

    if kind == "anp":
        qtd = round(rng.uniform(100, 15000), 4)
        preco = round(rng.uniform(4.5, 7.5), 4)
    elif kind == "service":
        qtd = float(rng.randint(1, 10))
        preco = round(rng.uniform(80, 5000), 2)
    else:
        qtd = (
            round(rng.uniform(1, 50), 4)
            if rng.random() < 0.3
            else float(rng.randint(1, 100))
        )
        preco = round(rng.uniform(2, 3000), 2)
    v_prod = _r2(qtd * preco)

    item = {
        "kind": kind,
        "cProd": rng.choice(
            [
                f"SKU{rng.randint(1000, 99999)}",
                f"{rng.randint(100000, 9999999)}",
                f"{name[:3].upper()}-{rng.randint(100, 999)}",
            ]
        ),
        "xProd": f"{name} {variante}",
        "NCM": f"{cat['ncm_prefix']}{rng.randint(0, 9999):04d}"
        if kind != "service"
        else "00",
        "CFOP": cfop,
        "uCom": cat["unit"],
        "_qtd": qtd,
        "_preco_unit": preco,
        "_v_prod": v_prod,
        "qCom": f"{qtd:.4f}",
        "vUnCom": f"{preco:.10f}",
        "vProd": _money(v_prod),
        "cListServ": cat.get("cListServ"),
        "anp": rng.choice(cat["anp"]) if kind == "anp" else None,
    }
    return item


def _apportion(total: float, weights):
    """Rateia `total` proporcionalmente aos pesos, fechando centavos no último."""
    s = sum(weights) or 1.0
    parts = [_r2(total * w / s) for w in weights]
    if parts:
        parts[-1] = _r2(total - sum(parts[:-1]))
    return parts


def _build_icms(imposto, ns, rng, profile, item):
    """Grupo <ICMS> conforme regime/CST. Retorna dict com valores numéricos."""
    icms = xml_builder.sub(imposto, "ICMS", ns)
    orig = rng.choices(["0", "1", "2", "5"], weights=[0.8, 0.08, 0.08, 0.04], k=1)[0]
    v_prod = item["_v_prod"]
    out = {
        "orig": orig,
        "vBC": 0.0,
        "pICMS": 0.0,
        "vICMS": 0.0,
        "vBCST": 0.0,
        "vST": 0.0,
    }

    if profile.regime in ("simples", "mei"):
        csosn = rng.choice(
            ["102", "102", "101", "103", "300", "400", "500", "900"]
            if profile.regime == "simples"
            else ["102", "102", "103", "500"]
        )
        grp = code_tables.CSOSN_GROUPS[csosn]
        g = xml_builder.sub(icms, grp["tag"], ns)
        xml_builder.sub_fields(g, ns, [("orig", orig), ("CSOSN", csosn)])
        if grp["credit"]:
            p_cred = rng.choice([1.25, 1.86, 2.56, 3.95])
            xml_builder.sub_fields(
                g,
                ns,
                [
                    ("pCredSN", f"{p_cred:.4f}"),
                    ("vCredICMSSN", _money(_r2(v_prod * p_cred / 100))),
                ],
            )
        elif csosn == "900":
            p = rng.choice([7.0, 12.0, 18.0])
            v = _r2(v_prod * p / 100)
            xml_builder.sub_fields(
                g,
                ns,
                [
                    ("modBC", "3"),
                    ("vBC", _money(v_prod)),
                    ("pICMS", f"{p:.4f}"),
                    ("vICMS", _money(v)),
                ],
            )
            out.update(vBC=v_prod, pICMS=p, vICMS=v)
        out["cst"] = csosn
        return out

    cst = rng.choices(
        list(code_tables.ICMS_CST_GROUPS.keys()),
        weights=[0.35, 0.12, 0.15, 0.1, 0.05, 0.13, 0.1],
        k=1,
    )[0]
    grp = code_tables.ICMS_CST_GROUPS[cst]
    g = xml_builder.sub(icms, grp["tag"], ns)
    xml_builder.sub_fields(g, ns, [("orig", orig), ("CST", cst)])
    out["cst"] = cst

    if cst == "60":
        p_st = rng.choice([17.0, 18.0, 20.0])
        v_bc_ret = _r2(v_prod * rng.uniform(1.2, 1.6))
        xml_builder.sub_fields(
            g,
            ns,
            [
                ("vBCSTRet", _money(v_bc_ret)),
                ("pST", f"{p_st:.4f}"),
                ("vICMSSubstituto", _money(_r2(v_bc_ret * 0.05))),
                ("vICMSSTRet", _money(_r2(v_bc_ret * p_st / 100))),
            ],
        )
        return out
    if not grp["bc"]:
        return out

    p_red = rng.choice([30.0, 41.67, 51.11, 61.11]) if grp["red"] else 0.0
    v_bc = _r2(v_prod * (1 - p_red / 100))
    p_icms = rng.choice([4.0, 7.0, 12.0, 17.0, 18.0, 19.0, 20.5])
    v_icms = _r2(v_bc * p_icms / 100)
    pairs = [("modBC", "3")]
    if grp["red"]:
        pairs.append(("pRedBC", f"{p_red:.4f}"))
    pairs += [
        ("vBC", _money(v_bc)),
        ("pICMS", f"{p_icms:.4f}"),
        ("vICMS", _money(v_icms)),
    ]
    xml_builder.sub_fields(g, ns, pairs)
    out.update(vBC=v_bc, pICMS=p_icms, vICMS=v_icms)

    if grp["st"]:
        mva = rng.choice([30.0, 40.0, 50.32, 71.78])
        v_bcst = _r2(v_prod * (1 + mva / 100))
        p_st = 18.0
        v_st = max(0.0, _r2(v_bcst * p_st / 100 - v_icms))
        xml_builder.sub_fields(
            g,
            ns,
            [
                ("modBCST", "4"),
                ("pMVAST", f"{mva:.4f}"),
                ("vBCST", _money(v_bcst)),
                ("pICMSST", f"{p_st:.4f}"),
                ("vICMSST", _money(v_st)),
            ],
        )
        out.update(vBCST=v_bcst, vST=v_st)
    return out


def _build_ipi(imposto, ns, rng, profile, item):
    if profile.regime != "normal":
        return {"vIPI": 0.0, "pIPI": 0.0}
    ipi = xml_builder.sub(imposto, "IPI", ns)
    xml_builder.sub(ipi, "cEnq", ns, "999")
    if profile.ipi_tributado and rng.random() < 0.8:
        p = rng.choice([3.25, 5.0, 6.5, 9.75, 15.0])
        v = _r2(item["_v_prod"] * p / 100)
        g = xml_builder.sub(ipi, "IPITrib", ns)
        xml_builder.sub_fields(
            g,
            ns,
            [
                ("CST", "50"),
                ("vBC", item["vProd"]),
                ("pIPI", f"{p:.4f}"),
                ("vIPI", _money(v)),
            ],
        )
        return {"vIPI": v, "pIPI": p}
    g = xml_builder.sub(ipi, "IPINT", ns)
    xml_builder.sub(g, "CST", ns, rng.choice(["51", "52", "53", "54", "55"]))
    return {"vIPI": 0.0, "pIPI": 0.0}


def _build_pis_cofins(imposto, ns, rng, profile, item, cumulativo):
    out = {}
    for tax, (p_cum, p_ncum) in (("PIS", (0.65, 1.65)), ("COFINS", (3.0, 7.6))):
        el = xml_builder.sub(imposto, tax, ns)
        if profile.regime == "normal":
            p = p_cum if cumulativo else p_ncum
            v = _r2(item["_v_prod"] * p / 100)
            g = xml_builder.sub(el, f"{tax}Aliq", ns)
            xml_builder.sub_fields(
                g,
                ns,
                [
                    ("CST", "01"),
                    ("vBC", item["vProd"]),
                    (f"p{tax}", f"{p:.4f}"),
                    (f"v{tax}", _money(v)),
                ],
            )
        else:
            v = 0.0
            g = xml_builder.sub(el, f"{tax}Outr", ns)
            xml_builder.sub_fields(
                g,
                ns,
                [
                    ("CST", "99"),
                    ("vBC", "0.00"),
                    (f"p{tax}", "0.0000"),
                    (f"v{tax}", "0.00"),
                ],
            )
        out[f"v{tax}"] = v
    return out


def _build_issqn(imposto, ns, rng, item, c_mun_fg):
    aliq = rng.choice([2.0, 3.0, 5.0])
    v_iss = _r2(item["_v_prod"] * aliq / 100)
    g = xml_builder.sub(imposto, "ISSQN", ns)
    xml_builder.sub_fields(
        g,
        ns,
        [
            ("vBC", item["vProd"]),
            ("vAliq", f"{aliq:.4f}"),
            ("vISSQN", _money(v_iss)),
            ("cMunFG", c_mun_fg),
            ("cListServ", item["cListServ"]),
            ("indISS", "1"),
            ("indIncentivo", "2"),
        ],
    )
    return {"vISSQN": v_iss, "aliqISS": aliq}


# Alíquotas-teste de 2026 (LC 214/2025): CBS 0,9%, IBS UF 0,1%, IBS Mun 0%.
_P_IBS_UF, _P_IBS_MUN, _P_CBS = 0.10, 0.0, 0.90


def _build_ibscbs(imposto, ns, item):
    v_bc = item["_v_prod"]
    v_uf = _r2(v_bc * _P_IBS_UF / 100)
    v_mun = _r2(v_bc * _P_IBS_MUN / 100)
    v_cbs = _r2(v_bc * _P_CBS / 100)
    g = xml_builder.sub(imposto, "IBSCBS", ns)
    xml_builder.sub_fields(g, ns, [("CST", "000"), ("cClassTrib", "000001")])
    gg = xml_builder.sub(g, "gIBSCBS", ns)
    xml_builder.sub(gg, "vBC", ns, _money(v_bc))
    uf = xml_builder.sub(gg, "gIBSUF", ns)
    xml_builder.sub_fields(
        uf, ns, [("pIBSUF", f"{_P_IBS_UF:.4f}"), ("vIBSUF", _money(v_uf))]
    )
    mun = xml_builder.sub(gg, "gIBSMun", ns)
    xml_builder.sub_fields(
        mun, ns, [("pIBSMun", f"{_P_IBS_MUN:.4f}"), ("vIBSMun", _money(v_mun))]
    )
    xml_builder.sub(gg, "vIBS", ns, _money(_r2(v_uf + v_mun)))
    cbs = xml_builder.sub(gg, "gCBS", ns)
    xml_builder.sub_fields(
        cbs, ns, [("pCBS", f"{_P_CBS:.4f}"), ("vCBS", _money(v_cbs))]
    )
    return {"vBCIBSCBS": v_bc, "vIBSUF": v_uf, "vIBSMun": v_mun, "vCBS": v_cbs}


def _fill_prod_extras(prod, ns, rng, item, emissao, uf):
    """<rastro> (ANVISA, às vezes outros) e <comb>/<med>, nessa ordem, no fim de <prod>."""
    rastros = []
    if item["kind"] == "anvisa" or (item["kind"] == "goods" and rng.random() < 0.05):
        for _ in range(rng.randint(1, 2)):
            d_fab = emissao.date() - datetime.timedelta(days=rng.randint(30, 400))
            d_val = d_fab + datetime.timedelta(days=rng.choice([365, 540, 730, 1095]))
            r = {
                "nLote": f"{rng.randint(10000, 99999999)}",
                "qLote": f"{max(1.0, item['_qtd'] * rng.uniform(0.3, 1.0)):.3f}",
                "dFab": d_fab.isoformat(),
                "dVal": d_val.isoformat(),
            }
            el = xml_builder.sub(prod, "rastro", ns)
            xml_builder.sub_fields(
                el, ns, [(k, r[k]) for k in ("nLote", "qLote", "dFab", "dVal")]
            )
            rastros.append(r)
    item["rastro"] = rastros
    if item["kind"] == "anvisa":
        med = {
            "cProdANVISA": f"1{rng.randint(0, 999999999999):012d}",
            "vPMC": _money(_r2(item["_preco_unit"] * rng.uniform(1.1, 1.6))),
        }
        el = xml_builder.sub(prod, "med", ns)
        xml_builder.sub_fields(
            el, ns, [("cProdANVISA", med["cProdANVISA"]), ("vPMC", med["vPMC"])]
        )
        item["med"] = med
    if item["kind"] == "anp":
        c_anp, desc_anp = item["anp"]
        el = xml_builder.sub(prod, "comb", ns)
        xml_builder.sub_fields(
            el, ns, [("cProdANP", c_anp), ("descANP", desc_anp), ("UFCons", uf)]
        )
        item["comb"] = {"cProdANP": c_anp, "descANP": desc_anp, "UFCons": uf}


_INF_AD_PROD = [
    "Garantia de {g} meses contra defeitos de fabricação.",
    "Pedido {n} item {k}.",
    "Produto conforme especificação técnica {n}.",
    "Lote de produção {n}.",
    "Item sujeito a substituição tributária.",
    "Cor: {cor}. Embalagem com {k} unidades.",
]


def _fill_det(det_el, ns, rng, profile, item, idx, extras):
    det_el.set("nItem", str(idx))
    prod = xml_builder.find_one(det_el, "prod", ns)
    for tag in ("cProd", "xProd", "NCM", "CFOP", "uCom", "qCom", "vUnCom", "vProd"):
        xml_builder.set_text(prod, tag, ns, item[tag])
    xml_builder.set_text(prod, "uTrib", ns, item["uCom"])
    xml_builder.set_text(prod, "qTrib", ns, item["qCom"])
    xml_builder.set_text(prod, "vUnTrib", ns, item["vUnCom"])
    if rng.random() < 0.3 and item["kind"] == "goods":
        ean = f"789{rng.randint(0, 9999999999):010d}"
        xml_builder.set_text(prod, "cEAN", ns, ean)
        xml_builder.set_text(prod, "cEANTrib", ns, ean)
    for tag in ("vFrete", "vSeg", "vDesc", "vOutro"):
        val = item[f"_{tag}"]
        if val > 0:
            xml_builder.set_text(prod, tag, ns, _money(val))
        else:
            xml_builder.remove(prod, tag, ns)
    _fill_prod_extras(prod, ns, rng, item, extras["emissao"], extras["dest_uf"])

    imposto = xml_builder.find_one(det_el, "imposto", ns)
    taxes = {}
    if item["kind"] == "service":
        taxes.update(_build_issqn(imposto, ns, rng, item, extras["c_mun_fg"]))
        taxes.update(
            {
                "vBC": 0.0,
                "vICMS": 0.0,
                "vBCST": 0.0,
                "vST": 0.0,
                "pICMS": 0.0,
                "vIPI": 0.0,
                "pIPI": 0.0,
                "cst": "",
                "orig": "",
            }
        )
    else:
        taxes.update(_build_icms(imposto, ns, rng, profile, item))
        taxes.update(_build_ipi(imposto, ns, rng, profile, item))
    taxes.update(
        _build_pis_cofins(imposto, ns, rng, profile, item, extras["cumulativo"])
    )
    if profile.ibs_cbs:
        taxes.update(_build_ibscbs(imposto, ns, item))
    v_tot_trib = _r2(item["_v_prod"] * rng.uniform(0.12, 0.38))
    xml_builder.set_text(imposto, "vTotTrib", ns, _money(v_tot_trib))
    taxes["vTotTrib"] = v_tot_trib
    item.update({f"_{k}": v for k, v in taxes.items() if isinstance(v, float)})
    item["CST"] = taxes.get("cst", "")
    item["orig"] = taxes.get("orig", "")
    item["vICMS"] = _money(taxes["vICMS"])
    item["vBC"] = _money(taxes["vBC"])
    item["vIPI"] = _money(taxes["vIPI"])

    if rng.random() < profile.inf_ad_prod_rate:
        txt = rng.choice(_INF_AD_PROD).format(
            g=rng.choice([3, 6, 12, 24]),
            n=rng.randint(1000, 999999),
            k=rng.randint(1, 24),
            cor=rng.choice(["Preto", "Branco", "Azul", "Cinza"]),
        )
        xml_builder.set_text(det_el, "infAdProd", ns, txt)
        item["infAdProd"] = txt
    else:
        xml_builder.remove(det_el, "infAdProd", ns)
        item["infAdProd"] = ""


# --------------------------------------------------------------------------
# Totais, cobrança, pagamento, infAdic, protocolo
# --------------------------------------------------------------------------


def _sum(items, key, kinds=None):
    return _r2(
        sum(i.get(key, 0.0) for i in items if kinds is None or i["kind"] in kinds)
    )


def _fill_totals(root, ns, profile, items, emissao):
    goods = ("goods", "anp", "anvisa")
    t = {
        "vBC": _sum(items, "_vBC"),
        "vICMS": _sum(items, "_vICMS"),
        "vBCST": _sum(items, "_vBCST"),
        "vST": _sum(items, "_vST"),
        "vProd": _sum(items, "_v_prod", goods),
        "vFrete": _sum(items, "_vFrete"),
        "vSeg": _sum(items, "_vSeg"),
        "vDesc": _sum(items, "_vDesc"),
        "vIPI": _sum(items, "_vIPI"),
        "vPIS": _sum(items, "_vPIS"),
        "vCOFINS": _sum(items, "_vCOFINS"),
        "vOutro": _sum(items, "_vOutro"),
        "vTotTrib": _sum(items, "_vTotTrib"),
    }
    services = [i for i in items if i["kind"] == "service"]
    t["vServ"] = _sum(services, "_v_prod")
    t["vISS"] = _sum(services, "_vISSQN")
    # Fórmula oficial (MOC NF-e, regra W16-xx), sem os termos sempre zero aqui
    t["vNF"] = _r2(
        t["vProd"]
        - t["vDesc"]
        + t["vST"]
        + t["vFrete"]
        + t["vSeg"]
        + t["vOutro"]
        + t["vIPI"]
        + t["vServ"]
    )

    base = "infNFe/total/ICMSTot"
    for k in (
        "vBC",
        "vICMS",
        "vBCST",
        "vST",
        "vProd",
        "vFrete",
        "vSeg",
        "vDesc",
        "vIPI",
        "vPIS",
        "vCOFINS",
        "vOutro",
        "vNF",
        "vTotTrib",
    ):
        xml_builder.set_text(root, f"{base}/{k}", ns, _money(t[k]))

    if services:
        xml_builder.set_text(
            root, "infNFe/total/ISSQNtot/vServ", ns, _money(t["vServ"])
        )
        xml_builder.set_text(root, "infNFe/total/ISSQNtot/vBC", ns, _money(t["vServ"]))
        xml_builder.set_text(root, "infNFe/total/ISSQNtot/vISS", ns, _money(t["vISS"]))
        xml_builder.set_text(
            root, "infNFe/total/ISSQNtot/dCompet", ns, emissao.date().isoformat()
        )
    else:
        xml_builder.remove(root, "infNFe/total/ISSQNtot", ns)

    if profile.ibs_cbs:
        b = "infNFe/total/IBSCBSTot"
        uf, mun, cbs = (
            _sum(items, "_vIBSUF"),
            _sum(items, "_vIBSMun"),
            _sum(items, "_vCBS"),
        )
        xml_builder.set_text(
            root, f"{b}/vBCIBSCBS", ns, _money(_sum(items, "_vBCIBSCBS"))
        )
        xml_builder.set_text(root, f"{b}/gIBS/gIBSUF/vIBSUF", ns, _money(uf))
        xml_builder.set_text(root, f"{b}/gIBS/gIBSMun/vIBSMun", ns, _money(mun))
        xml_builder.set_text(root, f"{b}/gIBS/vIBS", ns, _money(_r2(uf + mun)))
        xml_builder.set_text(root, f"{b}/gCBS/vCBS", ns, _money(cbs))
        t.update(vIBS=_r2(uf + mun), vCBS=cbs)
    else:
        xml_builder.remove(root, "infNFe/total/IBSCBSTot", ns)
    return t


def _fill_cobr_pag(root, ns, rng, profile, n_nf, v_nf, emissao):
    cobr = xml_builder.find_one(root, "infNFe/cobr", ns)
    dups = []
    if profile.cobr:
        n_dup = rng.choices([1, 2, 3, 4, 6], weights=[0.3, 0.25, 0.25, 0.1, 0.1], k=1)[
            0
        ]
        n_fat = n_nf if rng.random() < 0.6 else f"{n_nf}/{rng.randint(1, 9)}"
        xml_builder.set_text(cobr, "fat/nFat", ns, n_fat)
        xml_builder.set_text(cobr, "fat/vOrig", ns, _money(v_nf))
        xml_builder.set_text(cobr, "fat/vLiq", ns, _money(v_nf))
        values = _apportion(v_nf, [1.0] * n_dup)
        step = rng.choice([7, 14, 15, 28, 30])
        first = rng.choice([0, 7, 14, 28, 30])
        clones = xml_builder.clone_repeatable(root, "infNFe/cobr", "dup", ns, n_dup)
        for k, (el, v) in enumerate(zip(clones, values), start=1):
            d = {
                "nDup": f"{k:03d}",
                "dVenc": (
                    emissao.date() + datetime.timedelta(days=first + step * (k - 1))
                ).isoformat(),
                "vDup": _money(v),
            }
            for tag, val in d.items():
                xml_builder.set_text(el, tag, ns, val)
            dups.append(d)
        t_pag, ind_pag = "15", "1"
    else:
        xml_builder.remove(root, "infNFe/cobr", ns)
        n_fat = ""
        t_pag, ind_pag = rng.choice(code_tables.TP_PAG), "0"
    xml_builder.set_text(root, "infNFe/pag/detPag/indPag", ns, ind_pag)
    xml_builder.set_text(root, "infNFe/pag/detPag/tPag", ns, t_pag)
    xml_builder.set_text(root, "infNFe/pag/detPag/vPag", ns, _money(v_nf))
    return {"nFat": n_fat, "dups": dups, "tPag": t_pag}


def _fill_inf_adic(root, ns, rng, faker, profile):
    inf_cpl = ""
    if profile.inf_cpl:
        n = rng.choices([1, 3, 6, 14], weights=[0.35, 0.35, 0.2, 0.1], k=1)[0]
        sentences = [
            rng.choice(code_tables.INF_CPL_SENTENCES).format(
                n=rng.randint(1000, 999999), nome=fake_data.person_name(rng, faker)
            )
            for _ in range(n)
        ]
        inf_cpl = " ".join(sentences)
    inf_fisco = ""
    if rng.random() < 0.2:
        inf_fisco = f"Documento emitido por: {fake_data.person_name(rng, faker)}"

    if inf_cpl:
        xml_builder.set_text(root, "infNFe/infAdic/infCpl", ns, inf_cpl)
    else:
        xml_builder.remove(root, "infNFe/infAdic/infCpl", ns)
    if inf_fisco:
        xml_builder.set_text(root, "infNFe/infAdic/infAdFisco", ns, inf_fisco)
    else:
        xml_builder.remove(root, "infNFe/infAdic/infAdFisco", ns)
    if not inf_cpl and not inf_fisco:
        xml_builder.remove(root, "infNFe/infAdic", ns)
    return {"infCpl": inf_cpl, "infAdFisco": inf_fisco}


def _wrap_nfeproc(root, ns, rng, chave, emissao):
    proc = ET.Element(f"{{{ns}}}nfeProc", {"versao": "4.00"})
    proc.append(root)
    prot = xml_builder.sub(proc, "protNFe", ns)
    prot.set("versao", "4.00")
    inf = xml_builder.sub(prot, "infProt", ns)
    dh_rec = emissao + datetime.timedelta(seconds=rng.randint(2, 600))
    n_prot = "1" + "00" + emissao.strftime("%y") + f"{rng.randint(0, 9999999999):010d}"
    xml_builder.sub_fields(
        inf,
        ns,
        [
            ("tpAmb", "2"),  # regra anti-validade: protocolo também de homologação
            ("verAplic", "SYNTH-HOM"),
            ("chNFe", chave),
            ("dhRecbto", dh_rec.strftime("%Y-%m-%dT%H:%M:%S-03:00")),
            ("nProt", n_prot),
            (
                "digVal",
                "".join(
                    rng.choice(
                        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
                    )
                    for _ in range(27)
                )
                + "=",
            ),
            ("cStat", "100"),
            ("xMotivo", "Autorizado o uso da NF-e"),
        ],
    )
    return proc, {
        "nProt": n_prot,
        "dhRecbto": dh_rec.strftime("%Y-%m-%dT%H:%M:%S-03:00"),
    }


def _render_spec(profile, emissao=None, seed=None) -> dict:
    """Config do renderer (serializável; convertida em DanfeConfig por `render_kwargs`)."""
    erp = getattr(profile, "erp_style", "standard")
    if profile.font_courier:
        font_type = "Courier"
    elif getattr(profile, "font_helvetica", False):
        font_type = "Helvetica"
    else:
        font_type = "Times"

    if erp == "minimal_open":
        table_style = "open_bottom"
    elif erp in ("linx_autosystem", "xpert", "galago", "classic_landscape"):
        table_style = "full_vertical_grid"
    else:
        table_style = "full_frame"

    if erp == "linx_autosystem":
        cols_preset = "fuel_anp"
    elif erp == "xpert":
        cols_preset = "discount_liquid"
    else:
        cols_preset = "standard"

    dt_str = emissao.strftime("%d/%m/%Y %H:%M:%S") if emissao else "01/01/2025 12:00:00"
    sub_emit_credit = ""
    mid_page_credit = ""
    footer_left_text = ""
    footer_right_text = ""
    if erp == "linx_autosystem":
        footer_left_text = "LINX SISTEMAS E CONSULTORIA LTDA - AutoSystem 3.2.5.12 - www.linx.invalid"
    elif erp == "xpert":
        sub_emit_credit = "xpert v3.5 - xpert.invalid"
        footer_left_text = "(c)1993-2025 xpert v3.5 - xpert.invalid"
        footer_right_text = f"DATA E HORA DA IMPRESSÃO: {dt_str}"
    elif erp == "galago":
        mid_page_credit = "Implante esta NF-e na sua empresa: www.galago.invalid"
    elif erp == "minimal_open":
        footer_left_text = f"DATA E HORA DA IMPRESSÃO  {dt_str}"

    return {
        "receipt_pos": "bottom" if profile.receipt_bottom else "top",
        "font_type": font_type,
        # fonte grande só com Times: em Helvetica/Courier os números da tabela de
        # itens quebram no meio ("610 / 2"), o que não ocorre em DANFE real
        "font_size": "BIG" if (profile.font_big and font_type == "Times") else "SMALL",
        "display_pis_cofins": profile.display_pis_cofins,
        "invoice_display": "duplicates_only" if profile.duplicates_only else "full",
        "decimals": profile.decimals,
        "landscape": profile.landscape,
        "erp_style": erp,
        "has_logo": getattr(profile, "has_logo", False),
        "logo_seed": seed,
        "product_table_style": table_style,
        "product_columns_preset": cols_preset,
        "vertical_block_labels": getattr(profile, "vertical_block_labels", False),
        "sub_emit_credit": sub_emit_credit,
        "mid_page_credit": mid_page_credit,
        "footer_left_text": footer_left_text,
        "footer_right_text": footer_right_text,
    }


def render_kwargs(field_values: dict) -> dict:
    """field_values["_render"] -> kwargs de `Danfe(xml, **kwargs)`."""
    from renderers.danfe.config import (
        DanfeConfig,
        DecimalConfig,
        FontSize,
        FontType,
        FooterStamp,
        InvoiceDisplay,
        ProductColumnsPreset,
        ProductDescriptionConfig,
        ProductTableStyle,
        ReceiptPosition,
    )
    from generator.branding.logo_factory import generate_company_logo

    spec = field_values.get("_render")
    if not spec:
        return {}
    items = field_values.get("items", [])
    logo_buf = None
    if spec.get("has_logo"):
        logo_rng = random.Random(spec.get("logo_seed") or 0)
        erp = spec.get("erp_style", "standard")
        preferred_style = (
            "badge_seal" if erp == "galago" else ("fuel_shield" if erp in ("linx_autosystem", "xpert") else None)
        )
        logo_buf = generate_company_logo(
            logo_rng, field_values.get("emit_xNome", "EMPRESA"), style=preferred_style
        )
    return {
        "config": DanfeConfig(
            logo=logo_buf,
            receipt_pos=ReceiptPosition(spec["receipt_pos"]),
            font_type=FontType(spec["font_type"]),
            font_size=FontSize[spec["font_size"]],
            display_pis_cofins=spec["display_pis_cofins"],
            invoice_display=(
                InvoiceDisplay.DUPLICATES_ONLY
                if spec["invoice_display"] == "duplicates_only"
                else InvoiceDisplay.FULL_DETAILS
            ),
            decimal_config=DecimalConfig(
                price_precision=spec["decimals"], quantity_precision=spec["decimals"]
            ),
            product_description_config=ProductDescriptionConfig(
                display_branch=any(i.get("rastro") for i in items),
                display_anp=any(i.get("comb") for i in items),
                display_anvisa=any(i.get("med") for i in items),
            ),
            display_homologation_dest_warning=False,
            product_table_style=ProductTableStyle(spec.get("product_table_style", "full_frame")),
            product_columns_preset=ProductColumnsPreset(spec.get("product_columns_preset", "standard")),
            vertical_block_labels=bool(spec.get("vertical_block_labels", False)),
            sub_emit_credit=spec.get("sub_emit_credit", ""),
            mid_page_credit=spec.get("mid_page_credit", ""),
            footer_left_text=spec.get("footer_left_text", ""),
            footer_stamp=FooterStamp(text=spec.get("footer_right_text", "")),
        )
    }


# --------------------------------------------------------------------------
# Entrada pública
# --------------------------------------------------------------------------


def generate_danfe(
    seed=None,
    num_items=None,
    profile_overrides=None,
    cnpj_alnum_ratio=fake_data.DEFAULT_CNPJ_ALNUM_RATIO,
    erp_preset=None,
):
    rng = random.Random(seed)
    faker = Faker("pt_BR")
    faker.seed_instance(seed)
    ns = _NS

    overrides = dict(profile_overrides or {})
    if num_items is not None:
        overrides["n_items"] = num_items
    if erp_preset is not None:
        overrides.setdefault("erp_style", erp_preset)
        overrides.setdefault("has_logo", True)
        if erp_preset == "classic_landscape":
            overrides.setdefault("landscape", True)
            overrides.setdefault("vertical_block_labels", True)
        else:
            overrides.setdefault("landscape", False)
    profile = sample_profile(rng, overrides)

    root = xml_builder.load_template(_TEMPLATE_PATH).getroot()
    fv = {}

    fv.update(_fill_emit(root, ns, rng, faker, profile, cnpj_alnum_ratio))
    emit_end = fv["emit_endereco"]
    fv.update(
        _fill_dest(root, ns, rng, faker, profile, cnpj_alnum_ratio, emit_end["uf"])
    )
    interstate = fv["dest_endereco"]["uf"] != emit_end["uf"]

    for tag in ("retirada", "entrega"):
        if getattr(profile, tag):
            fv[tag] = _fill_location(root, ns, rng, faker, tag, cnpj_alnum_ratio)
        else:
            xml_builder.remove(root, f"infNFe/{tag}", ns)
            fv[tag] = None

    # --- ide ---
    emissao = fake_data.recent_datetime(rng)
    dh_emi = emissao.strftime("%Y-%m-%dT%H:%M:%S-03:00")
    serie = str(rng.choice([1, 1, 1, 2, 3, 10, 101]))
    n_nf = str(rng.randint(1, 999999))
    c_nf = f"{rng.randint(0, 99999999):08d}"
    nat_op = rng.choice(_NAT_OP["venda"] if rng.random() < 0.85 else _NAT_OP["outras"])
    ide = {
        "cUF": emit_end["municipality_code"][:2],
        "cNF": c_nf,
        "natOp": nat_op,
        "serie": serie,
        "nNF": n_nf,
        "dhEmi": dh_emi,
        "dhSaiEnt": dh_emi,
        "idDest": "2" if interstate else "1",
        "cMunFG": emit_end["municipality_code"],
        "tpImp": "2" if profile.landscape else "1",
        "tpAmb": "2",  # regra anti-validade não-negociável (PLANO_GERADOR.md 9.5)
        "indFinal": "1" if fv["dest_doc_type"] == "cpf" else rng.choice(["0", "1"]),
        "indPres": rng.choice(["0", "1", "2", "9"]),
    }
    for k, v in ide.items():
        xml_builder.set_text(root, f"infNFe/ide/{k}", ns, v)

    chave = fake_data.access_key(
        rng,
        cnpj_digits=fv["emit_cnpj"],
        serie=serie,
        numero=n_nf,
        emissao_aamm=emissao.strftime("%y%m"),
    )
    xml_builder.set_text(root, "infNFe/ide/cDV", ns, chave[-1])
    xml_builder.set_attr(root, "infNFe", ns, "Id", f"NFe{chave}")
    fv.update(
        {
            "dhEmi": dh_emi,
            "serie": serie,
            "nNF": n_nf,
            "cNF": c_nf,
            "natOp": nat_op,
            "tpAmb": "2",
            "chave_acesso": chave,
        }
    )

    # --- itens ---
    items = [_make_item(rng, profile, interstate) for _ in range(profile.n_items)]
    if profile.issqn and not any(i["kind"] == "service" for i in items):
        items[-1] = _make_item(rng, profile, interstate, force_service=True)

    weights = [i["_v_prod"] for i in items]
    doc_frete = (
        _r2(sum(weights) * rng.uniform(0.01, 0.08))
        if profile.frete_seguro_outros
        else 0.0
    )
    doc_seg = (
        _r2(sum(weights) * rng.uniform(0.002, 0.01))
        if profile.frete_seguro_outros and rng.random() < 0.5
        else 0.0
    )
    doc_outro = (
        _r2(sum(weights) * rng.uniform(0.002, 0.02))
        if profile.frete_seguro_outros and rng.random() < 0.3
        else 0.0
    )
    doc_desc = _r2(sum(weights) * rng.uniform(0.01, 0.1)) if profile.desconto else 0.0
    for key, total in (
        ("_vFrete", doc_frete),
        ("_vSeg", doc_seg),
        ("_vOutro", doc_outro),
        ("_vDesc", doc_desc),
    ):
        for item, part in zip(items, _apportion(total, weights)):
            item[key] = part

    extras = {
        "emissao": emissao,
        "dest_uf": fv["dest_endereco"]["uf"],
        "c_mun_fg": emit_end["municipality_code"],
        "cumulativo": rng.random() < 0.5,
    }
    clones = xml_builder.clone_repeatable(root, "infNFe", "det", ns, len(items))
    for idx, (det_el, item) in enumerate(zip(clones, items), start=1):
        _fill_det(det_el, ns, rng, profile, item, idx, extras)

    totals = _fill_totals(root, ns, profile, items, emissao)

    peso_base = sum(i["_qtd"] for i in items) * rng.uniform(0.1, 2.0)
    fv["transp"] = _fill_transp(
        root, ns, rng, faker, profile, cnpj_alnum_ratio, peso_base
    )
    fv["cobr"] = _fill_cobr_pag(root, ns, rng, profile, n_nf, totals["vNF"], emissao)
    fv.update(_fill_inf_adic(root, ns, rng, faker, profile))

    out_root = root
    fv["protocolo"] = None
    if profile.nfe_proc:
        out_root, fv["protocolo"] = _wrap_nfeproc(root, ns, rng, chave, emissao)

    fv.update(
        {
            "items": items,
            "totals": totals,
            "total_vProd": totals["vProd"],
            "total_vICMS": totals["vICMS"],
            "total_vPIS": totals["vPIS"],
            "total_vCOFINS": totals["vCOFINS"],
            "total_vNF": totals["vNF"],
            "_profile": profile.to_dict(),
            "_render": _render_spec(profile, emissao=emissao, seed=seed),
            "_template_id": TEMPLATE_ID,
            "_doc_formats": _doc_formats(fv),
        }
    )
    return xml_builder.to_string(out_root), fv


def _doc_formats(fv) -> dict:
    """Formato do identificador de cada parte (numérico/alfanumérico/CPF),
    para estratificar avaliação de OCR/KIE por formato de CNPJ."""
    out = {
        "emit": _doc_format(fv["emit_cnpj"], "cnpj"),
        "dest": _doc_format(fv["dest_doc"], fv["dest_doc_type"]),
    }
    for k in ("retirada", "entrega", "transp"):
        part = fv.get(k)
        if part:
            out[k] = _doc_format(part["doc"], part["doc_type"])
    return out
