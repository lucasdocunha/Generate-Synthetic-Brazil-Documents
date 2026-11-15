"""Adaptador fino do DACTE (PLANO_GERADOR.md secao 6.4).

PoC — simplificações explícitas: modal fixo em dutoviário (estrutura do
tpl_001), 1 componente de frete, 1 documento (NF-e) vinculado, sem protocolo
de autorização (protCTe) — o template já é um <CTe> "bare", o que também
simplifica a estratégia anti-validade (nenhum protocolo plausível-real para
inventar, ver PLANO_GERADOR.md secao 9.5).
"""

import random
from pathlib import Path

import yaml
from faker import Faker

from generator import fake_data, xml_builder

_SCHEMA_PATH = Path(__file__).resolve().parent / "schemas" / "dacte.yaml"
_TEMPLATE_PATH = (
    Path(__file__).resolve().parent / "templates" / "dacte" / "v1" / "tpl_001" / "source.xml"
)

with open(_SCHEMA_PATH, encoding="utf8") as _f:
    _SCHEMA = yaml.safe_load(_f)

_NS = _SCHEMA["namespace"]


def _party(rng, faker, with_email=True, alnum_ratio=fake_data.DEFAULT_CNPJ_ALNUM_RATIO):
    return {
        "cnpj": fake_data.cnpj(rng, alnum_ratio=alnum_ratio),
        "ie": fake_data.ie_stub(rng),
        "xNome": fake_data.company_name(rng, faker),
        "fone": fake_data.phone_number(rng, mobile=rng.random() < 0.5),
        "endereco": fake_data.address(rng, faker),
        "email": fake_data.email(faker) if with_email else None,
    }


def _fill_party(
    root, base_path, addr_path, party, ns, include_complement=True, with_ie=True, fone_in_address=False
):
    xml_builder.set_text(root, f"{base_path}/CNPJ", ns, party["cnpj"])
    if with_ie:
        xml_builder.set_text(root, f"{base_path}/IE", ns, party["ie"])
    xml_builder.set_text(root, f"{base_path}/xNome", ns, party["xNome"])
    fone_path = f"{addr_path}/fone" if fone_in_address else f"{base_path}/fone"
    xml_builder.set_text(root, fone_path, ns, party["fone"])
    xml_builder.set_address(root, addr_path, party["endereco"], ns, include_complement)
    if party["email"] is not None:
        try:
            xml_builder.set_text(root, f"{base_path}/email", ns, party["email"])
        except ValueError:
            pass


def generate_dacte(
    seed=None,
    num_documents=None,
    cnpj_alnum_ratio=fake_data.DEFAULT_CNPJ_ALNUM_RATIO,
):
    rng = random.Random(seed)
    faker = Faker("pt_BR")
    faker.seed_instance(seed)

    tree = xml_builder.load_template(_TEMPLATE_PATH)
    root = tree.getroot()
    ns = _NS

    field_values = {}

    emit = _party(rng, faker, with_email=False, alnum_ratio=cnpj_alnum_ratio)
    emit["xFant"] = fake_data.company_name(rng, faker)
    _fill_party(
        root,
        "infCte/emit",
        "infCte/emit/enderEmit",
        emit,
        ns,
        include_complement=False,
        fone_in_address=True,
    )
    xml_builder.set_text(root, "infCte/emit/xFant", ns, emit["xFant"])
    field_values["emit"] = emit

    rem = _party(rng, faker, alnum_ratio=cnpj_alnum_ratio)
    _fill_party(root, "infCte/rem", "infCte/rem/enderReme", rem, ns)
    rem["xFant"] = fake_data.company_name(rng, faker)
    xml_builder.set_text(root, "infCte/rem/xFant", ns, rem["xFant"])
    field_values["rem"] = rem

    exped = _party(rng, faker, alnum_ratio=cnpj_alnum_ratio)
    _fill_party(root, "infCte/exped", "infCte/exped/enderExped", exped, ns)
    field_values["exped"] = exped

    receb = _party(rng, faker, alnum_ratio=cnpj_alnum_ratio)
    _fill_party(root, "infCte/receb", "infCte/receb/enderReceb", receb, ns)
    field_values["receb"] = receb

    dest = _party(rng, faker, alnum_ratio=cnpj_alnum_ratio)
    _fill_party(root, "infCte/dest", "infCte/dest/enderDest", dest, ns)
    field_values["dest"] = dest

    # --- ide ---
    emissao = fake_data.recent_datetime(rng)
    dh_emi = emissao.strftime("%Y-%m-%dT%H:%M:%S-03:00")
    serie = "1"
    n_ct = str(rng.randint(1, 999999))
    cuf_real = emit["endereco"]["municipality_code"][:2]
    nat_op = rng.choice(["Venda", "Prestação de serviço de transporte", "Transferência"])

    xml_builder.set_text(root, "infCte/ide/cUF", ns, cuf_real)
    xml_builder.set_text(root, "infCte/ide/natOp", ns, nat_op)
    xml_builder.set_text(root, "infCte/ide/serie", ns, serie)
    xml_builder.set_text(root, "infCte/ide/nCT", ns, n_ct)
    xml_builder.set_text(root, "infCte/ide/dhEmi", ns, dh_emi)
    xml_builder.set_text(root, "infCte/ide/tpAmb", ns, "2")  # regra anti-validade nao-negociavel

    xml_builder.set_text(root, "infCte/ide/cMunIni", ns, emit["endereco"]["municipality_code"])
    xml_builder.set_text(root, "infCte/ide/xMunIni", ns, emit["endereco"]["municipality_name"])
    xml_builder.set_text(root, "infCte/ide/UFIni", ns, emit["endereco"]["uf"])
    xml_builder.set_text(root, "infCte/ide/cMunFim", ns, dest["endereco"]["municipality_code"])
    xml_builder.set_text(root, "infCte/ide/xMunFim", ns, dest["endereco"]["municipality_name"])
    xml_builder.set_text(root, "infCte/ide/UFFim", ns, dest["endereco"]["uf"])

    aamm = emissao.strftime("%y%m")
    chave = fake_data.access_key(
        rng,
        cnpj_digits=emit["cnpj"],
        serie=serie,
        numero=n_ct,
        emissao_aamm=aamm,
        modelo="57",
    )
    cdv = chave[-1]
    xml_builder.set_text(root, "infCte/ide/cDV", ns, cdv)
    xml_builder.set_attr(root, "infCte", ns, "Id", f"CTe{chave}")

    field_values.update({"dhEmi": dh_emi, "serie": serie, "nCT": n_ct, "chave_acesso": chave, "natOp": nat_op})

    # --- valores da prestação (internamente consistentes) ---
    v_frete = round(rng.uniform(30, 5000), 2)
    p_icms = rng.choice([0.0, 4.0, 7.0, 12.0, 18.0])
    v_icms = round(v_frete * p_icms / 100, 2)

    xml_builder.set_text(root, "infCte/vPrest/vTPrest", ns, f"{v_frete:.2f}")
    xml_builder.set_text(root, "infCte/vPrest/vRec", ns, f"{v_frete:.2f}")
    xml_builder.set_text(root, "infCte/vPrest/Comp/vComp", ns, f"{v_frete:.2f}")
    xml_builder.set_text(root, "infCte/imp/ICMS/ICMS00/vBC", ns, f"{v_frete:.2f}")
    xml_builder.set_text(root, "infCte/imp/ICMS/ICMS00/pICMS", ns, f"{p_icms:.2f}")
    xml_builder.set_text(root, "infCte/imp/ICMS/ICMS00/vICMS", ns, f"{v_icms:.2f}")

    field_values.update({"v_frete": v_frete, "v_icms": v_icms})

    # --- carga ---
    v_carga = round(rng.uniform(500, 50000), 2)
    descricao_carga = rng.choice(
        ["Materiais de construção", "Produtos eletrônicos", "Insumos agrícolas", "Autopeças", "Bebidas"]
    )
    xml_builder.set_text(root, "infCte/infCTeNorm/infCarga/vCarga", ns, f"{v_carga:.2f}")
    xml_builder.set_text(root, "infCte/infCTeNorm/infCarga/proPred", ns, descricao_carga)
    xml_builder.set_text(root, "infCte/infCTeNorm/infCarga/vCargaAverb", ns, f"{v_carga:.2f}")

    field_values.update({"v_carga": v_carga, "descricao_carga": descricao_carga})

    # --- QR sintético (dominio .invalid, gerador tem controle total) ---
    qr_payload = (
        f"https://consulta.dominio-sintetico.invalid/cte?chCTe={chave}"
        f"&tpAmb=2&nProt={rng.randint(0, 999999999999999):015d}"
    )
    xml_builder.set_text(root, "infCTeSupl/qrCodCTe", ns, qr_payload)
    field_values["qr_payload"] = qr_payload
    field_values["_doc_formats"] = {
        role: ("cnpj_alnum" if fake_data.is_alnum_cnpj(field_values[role]["cnpj"]) else "cnpj_numeric")
        for role in ("emit", "rem", "exped", "receb", "dest")
    }

    xml_str = xml_builder.to_string(root)
    return xml_str, field_values
