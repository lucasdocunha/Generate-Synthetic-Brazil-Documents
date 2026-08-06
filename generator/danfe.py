"""Adaptador fino do DANFE (PLANO_GERADOR.md secao 6.4).

Orquestra fake_data.py + xml_builder.py para produzir um XML de NF-e
sintético e válido o bastante para o renderizador `brazilfiscalreport.danfe`
processar sem modificação nenhuma. Expõe generate_danfe(seed) -> (xml_str,
field_values), o contrato usado pelo pipeline (PLANO_GERADOR.md secao 3).

PoC v0 — simplificações explícitas, não escondidas:
- Só o template tpl_001 (1 variante estrutural) é usado.
- Frete/desconto sempre zero (o template já vem assim, não são tocados).
- Família de CST do ICMS fixa em "20" (ver code_tables.py).
- Sem retirada/entrega, sem fatura/duplicatas, sem ISSQN, sem PIS/COFINS
  variando de família — diversidade estrutural completa (perfis
  minimal/standard/full) é um follow-up, não implementado aqui.
"""

import random
from pathlib import Path

import yaml
from faker import Faker

from generator import fake_data, xml_builder

_SCHEMA_PATH = Path(__file__).resolve().parent / "schemas" / "danfe.yaml"
_TEMPLATE_PATH = (
    Path(__file__).resolve().parent / "templates" / "danfe" / "v1" / "tpl_001" / "source.xml"
)

with open(_SCHEMA_PATH, encoding="utf8") as _f:
    _SCHEMA = yaml.safe_load(_f)

_NS = _SCHEMA["namespace"]


def _set_address(root, base_path, addr, ns):
    xml_builder.set_text(root, f"{base_path}/xLgr", ns, addr["street"])
    xml_builder.set_text(root, f"{base_path}/nro", ns, addr["number"])
    xml_builder.set_text(root, f"{base_path}/xCpl", ns, addr["complement"])
    xml_builder.set_text(root, f"{base_path}/xBairro", ns, addr["neighborhood"])
    xml_builder.set_text(root, f"{base_path}/cMun", ns, addr["municipality_code"])
    xml_builder.set_text(root, f"{base_path}/xMun", ns, addr["municipality_name"])
    xml_builder.set_text(root, f"{base_path}/UF", ns, addr["uf"])
    xml_builder.set_text(root, f"{base_path}/CEP", ns, addr["cep"])


def generate_danfe(seed=None, num_items=None):
    rng = random.Random(seed)
    faker = Faker("pt_BR")
    faker.seed_instance(seed)

    tree = xml_builder.load_template(_TEMPLATE_PATH)
    root = tree.getroot()
    ns = _NS

    field_values = {}

    # --- Emitente ---
    emit_cnpj = fake_data.cnpj(rng)
    emit_nome = fake_data.company_name(rng, faker)
    emit_fantasia = fake_data.company_name(rng, faker)
    emit_endereco = fake_data.address(rng, faker)
    emit_ie = fake_data.ie_stub(rng)
    emit_fone = fake_data.phone_number(rng, mobile=True)

    xml_builder.set_text(root, "infNFe/emit/CNPJ", ns, emit_cnpj)
    xml_builder.set_text(root, "infNFe/emit/xNome", ns, emit_nome)
    xml_builder.set_text(root, "infNFe/emit/xFant", ns, emit_fantasia)
    xml_builder.set_text(root, "infNFe/emit/IE", ns, emit_ie)
    _set_address(root, "infNFe/emit/enderEmit", emit_endereco, ns)
    xml_builder.set_text(root, "infNFe/emit/enderEmit/fone", ns, emit_fone)

    field_values.update(
        {
            "emit_cnpj": emit_cnpj,
            "emit_xNome": emit_nome,
            "emit_xFant": emit_fantasia,
            "emit_IE": emit_ie,
            "emit_endereco": emit_endereco,
            "emit_fone": emit_fone,
        }
    )

    # --- Destinatário ---
    dest_cpf = fake_data.cpf(rng)
    dest_nome = fake_data.person_name(rng, faker)
    dest_endereco = fake_data.address(rng, faker)
    dest_email = fake_data.email(faker)
    dest_fone = fake_data.phone_number(rng, mobile=False)

    xml_builder.set_text(root, "infNFe/dest/CPF", ns, dest_cpf)
    xml_builder.set_text(root, "infNFe/dest/xNome", ns, dest_nome)
    _set_address(root, "infNFe/dest/enderDest", dest_endereco, ns)
    xml_builder.set_text(root, "infNFe/dest/enderDest/fone", ns, dest_fone)
    xml_builder.set_text(root, "infNFe/dest/email", ns, dest_email)

    field_values.update(
        {
            "dest_cpf": dest_cpf,
            "dest_xNome": dest_nome,
            "dest_endereco": dest_endereco,
            "dest_email": dest_email,
            "dest_fone": dest_fone,
        }
    )

    # --- Identificação (ide) ---
    emissao = fake_data.recent_datetime(rng)
    dh_emi = emissao.strftime("%Y-%m-%dT%H:%M:%S-03:00")
    serie = "1"
    n_nf = str(rng.randint(1, 999999))
    c_nf = f"{rng.randint(0, 99999999):08d}"
    cuf_real = emit_endereco["municipality_code"][:2]
    nat_op = rng.choice(["Venda", "Venda de mercadoria", "Remessa", "Devolução de venda"])

    xml_builder.set_text(root, "infNFe/ide/cUF", ns, cuf_real)
    xml_builder.set_text(root, "infNFe/ide/cNF", ns, c_nf)
    xml_builder.set_text(root, "infNFe/ide/natOp", ns, nat_op)
    xml_builder.set_text(root, "infNFe/ide/serie", ns, serie)
    xml_builder.set_text(root, "infNFe/ide/nNF", ns, n_nf)
    xml_builder.set_text(root, "infNFe/ide/dhEmi", ns, dh_emi)
    xml_builder.set_text(root, "infNFe/ide/dhSaiEnt", ns, dh_emi)
    xml_builder.set_text(root, "infNFe/ide/cMunFG", ns, emit_endereco["municipality_code"])
    # Regra anti-validade não-negociável (PLANO_GERADOR.md 9.5): sempre
    # homologação, para que o renderizador acione seu próprio watermark
    # "SEM VALOR FISCAL" automaticamente, sem nenhum patch no renderer.
    xml_builder.set_text(root, "infNFe/ide/tpAmb", ns, "2")

    # --- Chave de acesso (PLANO_GERADOR.md 9.2) ---
    aamm = emissao.strftime("%y%m")
    chave = fake_data.access_key(
        rng,
        cnpj_digits=emit_cnpj,
        serie=serie,
        numero=n_nf,
        emissao_aamm=aamm,
    )
    # access_key() já usa cUF="00" internamente e cNF aleatório próprio —
    # para o PoC mantemos o cNF do ide e o embutido na chave independentes
    # (ambos aleatórios, nenhum dos dois é lido pelo renderer para nada além
    # de exibição), o que já é suficiente para a garantia de não-validade.
    cdv = chave[-1]
    xml_builder.set_text(root, "infNFe/ide/cDV", ns, cdv)
    xml_builder.set_attr(root, "infNFe", ns, "Id", f"NFe{chave}")

    field_values.update(
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

    # --- Itens de produto (repetível) ---
    n = num_items if num_items is not None else rng.randint(1, 8)
    clones = xml_builder.clone_repeatable(root, "infNFe", "det", ns, n)

    total_vprod = 0.0
    total_vbc = 0.0
    total_vicms = 0.0
    total_vpis = 0.0
    total_vcofins = 0.0
    items = []

    for idx, det_el in enumerate(clones, start=1):
        det_el.set("nItem", str(idx))
        item = fake_data.product_line(rng)
        _fill_det(det_el, item, ns)
        items.append(item)
        total_vprod += item["_v_prod"]
        total_vbc += item["_v_bc"]
        total_vicms += item["_v_icms"]
        total_vpis += item["_v_pis"]
        total_vcofins += item["_v_cofins"]

    xml_builder.set_text(root, "infNFe/total/ICMSTot/vBC", ns, f"{total_vbc:.2f}")
    xml_builder.set_text(root, "infNFe/total/ICMSTot/vICMS", ns, f"{total_vicms:.2f}")
    xml_builder.set_text(root, "infNFe/total/ICMSTot/vProd", ns, f"{total_vprod:.2f}")
    xml_builder.set_text(root, "infNFe/total/ICMSTot/vPIS", ns, f"{total_vpis:.2f}")
    xml_builder.set_text(root, "infNFe/total/ICMSTot/vCOFINS", ns, f"{total_vcofins:.2f}")
    xml_builder.set_text(root, "infNFe/total/ICMSTot/vNF", ns, f"{total_vprod:.2f}")
    xml_builder.set_text(root, "infNFe/pag/detPag/vPag", ns, f"{total_vprod:.2f}")

    field_values.update(
        {
            "items": items,
            "total_vProd": round(total_vprod, 2),
            "total_vICMS": round(total_vicms, 2),
            "total_vPIS": round(total_vpis, 2),
            "total_vCOFINS": round(total_vcofins, 2),
            "total_vNF": round(total_vprod, 2),
        }
    )

    xml_str = xml_builder.to_string(root)
    return xml_str, field_values


def _fill_det(det_el, item: dict, ns: str):
    xml_builder.set_text(det_el, "prod/cProd", ns, item["cProd"])
    xml_builder.set_text(det_el, "prod/xProd", ns, item["xProd"])
    xml_builder.set_text(det_el, "prod/NCM", ns, item["NCM"])
    xml_builder.set_text(det_el, "prod/CFOP", ns, item["CFOP"])
    xml_builder.set_text(det_el, "prod/uCom", ns, item["uCom"])
    xml_builder.set_text(det_el, "prod/qCom", ns, item["qCom"])
    xml_builder.set_text(det_el, "prod/vUnCom", ns, item["vUnCom"])
    xml_builder.set_text(det_el, "prod/vProd", ns, item["vProd"])
    xml_builder.set_text(det_el, "prod/uTrib", ns, item["uCom"])
    xml_builder.set_text(det_el, "prod/qTrib", ns, item["qCom"])
    xml_builder.set_text(det_el, "prod/vUnTrib", ns, item["vUnCom"])

    xml_builder.set_text(det_el, "imposto/ICMS/ICMS20/CST", ns, item["CST"])
    xml_builder.set_text(det_el, "imposto/ICMS/ICMS20/pRedBC", ns, item["pRedBC"])
    xml_builder.set_text(det_el, "imposto/ICMS/ICMS20/vBC", ns, item["vBC"])
    xml_builder.set_text(det_el, "imposto/ICMS/ICMS20/pICMS", ns, item["pICMS"])
    xml_builder.set_text(det_el, "imposto/ICMS/ICMS20/vICMS", ns, item["vICMS"])

    xml_builder.set_text(det_el, "imposto/PIS/PISAliq/vBC", ns, item["vBC_pis_cofins"])
    xml_builder.set_text(det_el, "imposto/PIS/PISAliq/pPIS", ns, item["pPIS"])
    xml_builder.set_text(det_el, "imposto/PIS/PISAliq/vPIS", ns, item["vPIS"])

    xml_builder.set_text(det_el, "imposto/COFINS/COFINSAliq/vBC", ns, item["vBC_pis_cofins"])
    xml_builder.set_text(det_el, "imposto/COFINS/COFINSAliq/pCOFINS", ns, item["pCOFINS"])
    xml_builder.set_text(det_el, "imposto/COFINS/COFINSAliq/vCOFINS", ns, item["vCOFINS"])
