"""Adaptador fino do DAMDFE (PLANO_GERADOR.md secao 6.4).

PoC — simplificação explícita: modal fixo em aéreo (estrutura do tpl_001),
1 município de descarga, 1 NF-e vinculada.
"""

import random
from pathlib import Path

import yaml
from faker import Faker

from generator import fake_data, xml_builder

_SCHEMA_PATH = Path(__file__).resolve().parent / "schemas" / "damdfe.yaml"
_TEMPLATE_PATH = (
    Path(__file__).resolve().parent / "templates" / "damdfe" / "v1" / "tpl_001" / "source.xml"
)

with open(_SCHEMA_PATH, encoding="utf8") as _f:
    _SCHEMA = yaml.safe_load(_f)

_NS = _SCHEMA["namespace"]

_AIRCRAFT_PREFIXES = ["PP", "PR", "PT", "PS"]


def generate_damdfe(seed=None):
    rng = random.Random(seed)
    faker = Faker("pt_BR")
    faker.seed_instance(seed)

    tree = xml_builder.load_template(_TEMPLATE_PATH)
    root = tree.getroot()
    ns = _NS

    field_values = {}

    emit_cnpj = fake_data.cnpj(rng)
    emit_nome = fake_data.company_name(rng, faker)
    emit_fantasia = fake_data.company_name(rng, faker)
    emit_ie = fake_data.ie_stub(rng)
    emit_endereco = fake_data.address(rng, faker)
    emit_fone = fake_data.phone_number(rng, mobile=False)
    emit_email = fake_data.email(faker)

    xml_builder.set_text(root, "infMDFe/emit/CNPJ", ns, emit_cnpj)
    xml_builder.set_text(root, "infMDFe/emit/IE", ns, emit_ie)
    xml_builder.set_text(root, "infMDFe/emit/xNome", ns, emit_nome)
    xml_builder.set_text(root, "infMDFe/emit/xFant", ns, emit_fantasia)
    xml_builder.set_address(root, "infMDFe/emit/enderEmit", emit_endereco, ns, include_complement=False)
    xml_builder.set_text(root, "infMDFe/emit/enderEmit/fone", ns, emit_fone)
    xml_builder.set_text(root, "infMDFe/emit/enderEmit/email", ns, emit_email)

    field_values.update(
        {
            "emit_cnpj": emit_cnpj,
            "emit_xNome": emit_nome,
            "emit_xFant": emit_fantasia,
            "emit_IE": emit_ie,
            "emit_endereco": emit_endereco,
            "emit_fone": emit_fone,
            "emit_email": emit_email,
        }
    )

    emissao = fake_data.recent_datetime(rng)
    dh_emi = emissao.strftime("%Y-%m-%dT%H:%M:%S-03:00")
    serie = "1"
    n_mdf = str(rng.randint(1, 999999))
    cuf_real = emit_endereco["municipality_code"][:2]

    xml_builder.set_text(root, "infMDFe/ide/cUF", ns, cuf_real)
    xml_builder.set_text(root, "infMDFe/ide/serie", ns, serie)
    xml_builder.set_text(root, "infMDFe/ide/nMDF", ns, n_mdf)
    xml_builder.set_text(root, "infMDFe/ide/dhEmi", ns, dh_emi)
    xml_builder.set_text(root, "infMDFe/ide/UFIni", ns, emit_endereco["uf"])
    xml_builder.set_text(root, "infMDFe/ide/tpAmb", ns, "2")  # regra anti-validade nao-negociavel

    xml_builder.set_text(root, "infMDFe/ide/infMunCarrega/cMunCarrega", ns, emit_endereco["municipality_code"])
    xml_builder.set_text(root, "infMDFe/ide/infMunCarrega/xMunCarrega", ns, emit_endereco["municipality_name"])

    aamm = emissao.strftime("%y%m")
    chave = fake_data.access_key(
        rng, cnpj_digits=emit_cnpj, serie=serie, numero=n_mdf, emissao_aamm=aamm, modelo="58"
    )
    xml_builder.set_attr(root, "infMDFe", ns, "Id", f"MDFe{chave}")

    field_values.update({"dhEmi": dh_emi, "serie": serie, "nMDF": n_mdf, "chave_acesso": chave})

    # --- modal aereo ---
    aircraft = rng.choice(_AIRCRAFT_PREFIXES) + f"-{rng.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')}{rng.randint(100, 999)}"
    n_voo = str(rng.randint(1000, 9999))
    d_voo = emissao.strftime("%Y-%m-%d")
    xml_builder.set_text(root, "infMDFe/infModal/aereo/matr", ns, aircraft)
    xml_builder.set_text(root, "infMDFe/infModal/aereo/nVoo", ns, n_voo)
    xml_builder.set_text(root, "infMDFe/infModal/aereo/dVoo", ns, d_voo)
    field_values.update({"aircraft": aircraft, "n_voo": n_voo, "d_voo": d_voo})

    # --- documento vinculado + destino ---
    dest_mun_code, dest_mun_name, dest_uf = rng.choice(fake_data.load_municipios())
    xml_builder.set_text(root, "infMDFe/ide/UFFim", ns, dest_uf)
    xml_builder.set_text(root, "infMDFe/infDoc/infMunDescarga/cMunDescarga", ns, dest_mun_code)
    xml_builder.set_text(root, "infMDFe/infDoc/infMunDescarga/xMunDescarga", ns, dest_mun_name)

    chave_nfe_vinculada = fake_data.access_key(
        rng, cnpj_digits=fake_data.cnpj(rng), serie="1", numero=str(rng.randint(1, 999999)), emissao_aamm=aamm
    )
    xml_builder.set_text(root, "infMDFe/infDoc/infMunDescarga/infNFe/chNFe", ns, chave_nfe_vinculada)
    field_values["chave_nfe_vinculada"] = chave_nfe_vinculada

    # --- totais ---
    v_carga = round(rng.uniform(500, 80000), 2)
    q_carga = round(rng.uniform(10, 5000), 4)
    xml_builder.set_text(root, "infMDFe/tot/vCarga", ns, f"{v_carga:.2f}")
    xml_builder.set_text(root, "infMDFe/tot/qCarga", ns, f"{q_carga:.4f}")
    field_values.update({"v_carga": v_carga, "q_carga": q_carga})

    # --- QR sintetico ---
    qr_payload = (
        f"https://consulta.dominio-sintetico.invalid/mdfe?chMDFe={chave}&tpAmb=2"
        f"&nProt={rng.randint(0, 999999999999999):015d}"
    )
    xml_builder.set_text(root, "infMDFeSupl/qrCodMDFe", ns, qr_payload)
    field_values["qr_payload"] = qr_payload

    xml_str = xml_builder.to_string(root)
    return xml_str, field_values
