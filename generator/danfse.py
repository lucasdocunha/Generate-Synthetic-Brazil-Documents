"""Adaptador fino do DANFSE (PLANO_GERADOR.md secao 6.4).

PoC — simplificação explícita: 1 serviço, sem intermediário, sem RTC/IBS-CBS.

Nota anti-validade (PLANO_GERADOR.md 9.4): o domínio do QR está hardcoded no
renderer (`www.nfse.gov.br`, portal nacional real) e não é alterado aqui —
decisão desta rodada de manter o renderizador intocado. Como a chave
embutida deriva de um CNPJ com checksum deliberadamente inválido, uma
consulta real a esse portal responderia "não encontrada", o que já cumpre
o objetivo de não confundir com um documento real.
"""

import random
from pathlib import Path

import yaml
from faker import Faker

from generator import fake_data, xml_builder

_SCHEMA_PATH = Path(__file__).resolve().parent / "schemas" / "danfse.yaml"
_TEMPLATE_PATH = (
    Path(__file__).resolve().parent / "templates" / "danfse" / "v1" / "tpl_001" / "source.xml"
)

with open(_SCHEMA_PATH, encoding="utf8") as _f:
    _SCHEMA = yaml.safe_load(_f)

_NS = _SCHEMA["namespace"]

_SERVICE_CATALOG = [
    ("010501", "Serviço de consultoria em tecnologia da informação"),
    ("140501", "Serviço de manutenção e reparo predial"),
    ("170501", "Serviço de assessoria contábil"),
    ("010199", "Serviço de desenvolvimento de software sob encomenda"),
    ("070501", "Serviço de limpeza e conservação"),
]


def generate_danfse(seed=None):
    rng = random.Random(seed)
    faker = Faker("pt_BR")
    faker.seed_instance(seed)

    tree = xml_builder.load_template(_TEMPLATE_PATH)
    root = tree.getroot()
    ns = _NS

    field_values = {}

    cnpj = fake_data.cnpj(rng)
    nome = fake_data.company_name(rng, faker)
    _, municipality_name, _ = rng.choice(fake_data.load_municipios())

    xml_builder.set_text(root, "infNFSe/xLocEmi", ns, municipality_name)
    xml_builder.set_text(root, "infNFSe/xLocPrestacao", ns, municipality_name)
    xml_builder.set_text(root, "infNFSe/ambGer", ns, "2")
    xml_builder.set_text(root, "infNFSe/emit/CNPJ", ns, cnpj)
    xml_builder.set_text(root, "infNFSe/emit/xNome", ns, nome)
    xml_builder.set_text(root, "infNFSe/DPS/infDPS/prest/CNPJ", ns, cnpj)
    xml_builder.set_text(root, "infNFSe/DPS/infDPS/tpAmb", ns, "2")  # regra anti-validade nao-negociavel

    n_nfse = str(rng.randint(1, 999999))
    n_dps = n_nfse
    serie = "1"
    xml_builder.set_text(root, "infNFSe/nNFSe", ns, n_nfse)
    xml_builder.set_text(root, "infNFSe/DPS/infDPS/nDPS", ns, n_dps)
    xml_builder.set_text(root, "infNFSe/DPS/infDPS/serie", ns, serie)

    emissao = fake_data.recent_datetime(rng)
    dh_emi = emissao.strftime("%Y-%m-%dT%H:%M:%S-03:00")
    d_compet = emissao.strftime("%Y-%m-%d")
    xml_builder.set_text(root, "infNFSe/dhProc", ns, dh_emi)
    xml_builder.set_text(root, "infNFSe/DPS/infDPS/dhEmi", ns, dh_emi)
    xml_builder.set_text(root, "infNFSe/DPS/infDPS/dCompet", ns, d_compet)

    c_trib_nac, x_desc_serv = rng.choice(_SERVICE_CATALOG)
    v_serv = round(rng.uniform(200, 30000), 2)
    xml_builder.set_text(root, "infNFSe/DPS/infDPS/serv/cServ/cTribNac", ns, c_trib_nac)
    xml_builder.set_text(root, "infNFSe/DPS/infDPS/serv/cServ/xDescServ", ns, x_desc_serv)
    xml_builder.set_text(root, "infNFSe/DPS/infDPS/valores/vServPrest/vServ", ns, f"{v_serv:.2f}")
    xml_builder.set_text(root, "infNFSe/valores/vLiq", ns, f"{v_serv:.2f}")

    # A chave (Id do infNFSe) segue um formato do ADN nacional distinto do
    # padrao de 44 digitos NFe/CTe/MDFe, com checksum ainda nao confirmado
    # (PLANO_GERADOR.md, Questoes em aberto #2) — gerada como string numerica
    # do mesmo tamanho (50 digitos), sem alegacao de validade.
    key_nfse = "".join(str(rng.randint(0, 9)) for _ in range(50))
    xml_builder.set_attr(root, "infNFSe", ns, "Id", f"NFS{key_nfse}")

    field_values.update(
        {
            "emit_cnpj": cnpj,
            "emit_xNome": nome,
            "municipality_name": municipality_name,
            "nNFSe": n_nfse,
            "dhEmi": dh_emi,
            "cTribNac": c_trib_nac,
            "xDescServ": x_desc_serv,
            "vServ": v_serv,
            "key_nfse": key_nfse,
        }
    )

    xml_str = xml_builder.to_string(root)
    return xml_str, field_values
