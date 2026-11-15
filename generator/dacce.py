"""Adaptador fino do DACCe (PLANO_GERADOR.md secao 6.4).

DACCe é o tipo mais atípico entre os 5: sem classe de Config, sem
paginação, e sem NENHUM mecanismo de watermark no renderizador — a proteção
anti-validade recai inteiramente sobre a chave de acesso (chNFe) ter
checksum deliberadamente corrompido (PLANO_GERADOR.md secao 9.1/9.2/9.5).
O construtor `DaCCe(xml, emitente, image)` também recebe o emitente FORA do
XML, como um dict — diferente dos outros 4 tipos.
"""

import random
from pathlib import Path

import yaml
from faker import Faker

from generator import fake_data, xml_builder

_SCHEMA_PATH = Path(__file__).resolve().parent / "schemas" / "dacce.yaml"
_TEMPLATE_PATH = (
    Path(__file__).resolve().parent / "templates" / "dacce" / "v1" / "tpl_001" / "source.xml"
)

with open(_SCHEMA_PATH, encoding="utf8") as _f:
    _SCHEMA = yaml.safe_load(_f)

_NS = _SCHEMA["namespace"]

_CORRECAO_MOTIVOS = [
    "Correção do CFOP do item 1, informado incorretamente na nota original.",
    "Correção da descrição do produto, sem alteração de valor.",
    "Correção do endereço do destinatário informado na nota original.",
    "Correção da data de saída da mercadoria.",
]


def generate_dacce(seed=None, cnpj_alnum_ratio=fake_data.DEFAULT_CNPJ_ALNUM_RATIO):
    rng = random.Random(seed)
    faker = Faker("pt_BR")
    faker.seed_instance(seed)

    tree = xml_builder.load_template(_TEMPLATE_PATH)
    root = tree.getroot()
    ns = _NS

    field_values = {}

    autor_cnpj = fake_data.cnpj(rng, alnum_ratio=cnpj_alnum_ratio)
    dest_cnpj = fake_data.cnpj(rng, alnum_ratio=cnpj_alnum_ratio)

    emissao = fake_data.recent_datetime(rng)
    dh_evento = emissao.strftime("%Y-%m-%dT%H:%M:%S-03:00")
    dh_reg = (emissao).strftime("%Y-%m-%dT%H:%M:%S-03:00")

    aamm = emissao.strftime("%y%m")
    serie = "1"
    n_nf = str(rng.randint(1, 999999))
    chave_nfe = fake_data.access_key(
        rng, cnpj_digits=dest_cnpj, serie=serie, numero=n_nf, emissao_aamm=aamm
    )

    xml_builder.set_text(root, "evento/infEvento/CNPJ", ns, autor_cnpj)
    xml_builder.set_text(root, "evento/infEvento/chNFe", ns, chave_nfe)
    xml_builder.set_text(root, "evento/infEvento/dhEvento", ns, dh_evento)
    xml_builder.set_text(root, "evento/infEvento/tpAmb", ns, "2")  # regra anti-validade nao-negociavel

    xcorrecao = rng.choice(_CORRECAO_MOTIVOS)
    xml_builder.set_text(root, "evento/infEvento/detEvento/xCorrecao", ns, xcorrecao)

    xml_builder.set_text(root, "retEvento/infEvento/tpAmb", ns, "2")
    xml_builder.set_text(root, "retEvento/infEvento/dhRegEvento", ns, dh_reg)
    xml_builder.set_text(root, "retEvento/infEvento/chNFe", ns, chave_nfe)
    xml_builder.set_text(root, "retEvento/infEvento/CNPJDest", ns, dest_cnpj)
    n_prot = "".join(str(rng.randint(0, 9)) for _ in range(15))
    xml_builder.set_text(root, "retEvento/infEvento/nProt", ns, n_prot)

    field_values.update(
        {
            "autor_cnpj": autor_cnpj,
            "dest_cnpj": dest_cnpj,
            "chave_nfe": chave_nfe,
            "dh_evento": dh_evento,
            "xcorrecao": xcorrecao,
            "n_prot": n_prot,
        }
    )

    emitente_endereco = fake_data.address(rng, faker)
    emitente = {
        "nome": fake_data.company_name(rng, faker),
        "end": f"{emitente_endereco['street']}, {emitente_endereco['number']}",
        "bairro": emitente_endereco["neighborhood"],
        "cidade": emitente_endereco["municipality_name"],
        "uf": emitente_endereco["uf"],
        "fone": fake_data.phone_number(rng, mobile=True),
    }
    field_values["emitente"] = emitente
    field_values["_doc_formats"] = {
        "autor": "cnpj_alnum" if fake_data.is_alnum_cnpj(autor_cnpj) else "cnpj_numeric",
        "dest": "cnpj_alnum" if fake_data.is_alnum_cnpj(dest_cnpj) else "cnpj_numeric",
    }

    xml_str = xml_builder.to_string(root)
    return xml_str, emitente, field_values
