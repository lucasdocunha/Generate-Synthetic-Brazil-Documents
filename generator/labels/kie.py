"""Derivação do bloco KIE do label canônico (PLANO_GERADOR.md secao 13).

`field_id_to_element` (produzido por generator/labels/layout.py, via
extração/casamento pós-renderização — ver PLANO_GERADOR.md, "Questões em
aberto" #1, revisitada) mapeia o mesmo conjunto de chaves usado em
`layout.flatten_danfe_fields` para o `element_id` do bbox correspondente.
Quando `field_id_to_element` não é passado (ou uma chave não deu match),
`bbox_ref` fica `None` — nem todo campo tem uma chamada de desenho própria
e isolada (ver nota no PLANO_GERADOR.md sobre bbox_ref nulo ser normal).
"""


def _leaf(value, field_key, field_id_to_element, raw_value=None):
    field_id_to_element = field_id_to_element or {}
    return {
        "value": value,
        "raw_value": raw_value if raw_value is not None else value,
        "bbox_ref": field_id_to_element.get(field_key),
    }


def build_kie_danfe(field_values: dict, field_id_to_element: dict = None) -> dict:
    m = field_id_to_element
    emit_end = field_values["emit_endereco"]
    dest_end = field_values["dest_endereco"]

    items = []
    for idx, item in enumerate(field_values["items"], start=1):
        p = f"item_{idx}_"
        items.append(
            {
                "index": idx,
                "code": _leaf(item["cProd"], p + "codigo", m),
                "description": _leaf(item["xProd"], p + "descricao", m),
                "ncm": _leaf(item["NCM"], p + "ncm", m),
                "cfop": _leaf(item["CFOP"], p + "cfop", m),
                "unit": _leaf(item["uCom"], p + "unidade", m),
                "quantity": _leaf(item["qCom"], p + "qtd", m, raw_value=item["_qtd"]),
                "unit_price": _leaf(item["vUnCom"], p + "vunit", m, raw_value=item["_preco_unit"]),
                "total_price": _leaf(item["vProd"], p + "vtotal", m, raw_value=item["_v_prod"]),
                "icms_value": _leaf(item["vICMS"], p + "vicms", m, raw_value=item["_v_icms"]),
            }
        )

    return {
        "issuer": {
            "cnpj": _leaf(field_values["emit_cnpj"], "emit_cnpj_cpf", m),
            "name": _leaf(field_values["emit_xNome"], "emit_xNome", m),
            "fantasy_name": _leaf(field_values["emit_xFant"], "emit_xFant", m),
            "address": {
                "street": _leaf(emit_end["street"], "emit_endereco_logradouro", m),
                "number": _leaf(emit_end["number"], "emit_endereco_numero", m),
                "neighborhood": _leaf(emit_end["neighborhood"], "emit_endereco_bairro", m),
                "municipality": _leaf(emit_end["municipality_name"], "emit_endereco_municipio", m),
                "uf": _leaf(emit_end["uf"], "emit_endereco_uf", m),
                "cep": _leaf(emit_end["cep"], "emit_endereco_cep", m),
            },
        },
        "recipient": {
            "cpf": _leaf(field_values["dest_cpf"], "dest_cnpj_cpf", m),
            "name": _leaf(field_values["dest_xNome"], "dest_xNome", m),
            "address": {
                "street": _leaf(dest_end["street"], "dest_endereco_logradouro", m),
                "number": _leaf(dest_end["number"], "dest_endereco_numero", m),
                "neighborhood": _leaf(dest_end["neighborhood"], "dest_endereco_bairro", m),
                "municipality": _leaf(dest_end["municipality_name"], "dest_endereco_municipio", m),
                "uf": _leaf(dest_end["uf"], "dest_endereco_uf", m),
                "cep": _leaf(dest_end["cep"], "dest_endereco_cep", m),
            },
        },
        "document": {
            "number": _leaf(field_values["nNF"], "ident_numero", m),
            "series": _leaf(field_values["serie"], "ident_serie", m),
            "issue_date": _leaf(field_values["dhEmi"], "data_emissao", m),
            "access_key": _leaf(field_values["chave_acesso"], "chave_acesso", m),
            "environment": _leaf("homologacao", "__no_bbox__", m),
            "nature_of_operation": _leaf(field_values["natOp"], "natureza_operacao", m),
        },
        "totals": {
            "total_value": _leaf(
                f"{field_values['total_vNF']:.2f}", "total_vnf", m, raw_value=field_values["total_vNF"]
            ),
            "icms_total": _leaf(
                f"{field_values['total_vICMS']:.2f}", "total_vicms", m, raw_value=field_values["total_vICMS"]
            ),
            "discount": _leaf("0.00", "__no_bbox__", m, raw_value=0.0),
            "freight": _leaf("0.00", "__no_bbox__", m, raw_value=0.0),
        },
        "items": items,
    }


def build_kie_dacte(field_values: dict, field_id_to_element: dict = None) -> dict:
    m = field_id_to_element

    def party(role):
        p = field_values[role]
        e = p["endereco"]
        return {
            "cnpj": _leaf(p["cnpj"], f"{role}_cnpj", m),
            "name": _leaf(p["xNome"], f"{role}_xNome", m),
            "address": {
                "street": _leaf(e["street"], f"{role}_endereco_logradouro", m),
                "municipality": _leaf(e["municipality_name"], f"{role}_endereco_municipio", m),
                "uf": _leaf(e["uf"], f"{role}_endereco_uf", m),
                "cep": _leaf(e["cep"], f"{role}_endereco_cep", m),
            },
        }

    return {
        "issuer": party("emit"),
        "sender": party("rem"),
        "shipper": party("exped"),
        "receiver": party("receb"),
        "recipient": party("dest"),
        "document": {
            "number": _leaf(field_values["nCT"], "ident_numero", m),
            "series": _leaf(field_values["serie"], "ident_serie", m),
            "issue_date": _leaf(field_values["dhEmi"], "data_emissao", m),
            "access_key": _leaf(field_values["chave_acesso"], "chave_acesso", m),
            "environment": _leaf("homologacao", "__no_bbox__", m),
            "nature_of_operation": _leaf(field_values["natOp"], "natureza_operacao", m),
        },
        "totals": {
            "freight_value": _leaf(
                f"{field_values['v_frete']:.2f}", "v_frete", m, raw_value=field_values["v_frete"]
            ),
            "icms_value": _leaf(
                f"{field_values['v_icms']:.2f}", "v_icms", m, raw_value=field_values["v_icms"]
            ),
        },
        "cargo": {
            "value": _leaf(
                f"{field_values['v_carga']:.2f}", "v_carga", m, raw_value=field_values["v_carga"]
            ),
            "description": _leaf(field_values["descricao_carga"], "descricao_carga", m),
        },
    }


def build_kie_damdfe(field_values: dict, field_id_to_element: dict = None) -> dict:
    m = field_id_to_element
    e = field_values["emit_endereco"]
    return {
        "issuer": {
            "cnpj": _leaf(field_values["emit_cnpj"], "emit_cnpj", m),
            "name": _leaf(field_values["emit_xNome"], "emit_xNome", m),
            "fantasy_name": _leaf(field_values["emit_xFant"], "emit_xFant", m),
            "address": {
                "street": _leaf(e["street"], "emit_endereco_logradouro", m),
                "municipality": _leaf(e["municipality_name"], "emit_endereco_municipio", m),
                "uf": _leaf(e["uf"], "emit_endereco_uf", m),
                "cep": _leaf(e["cep"], "emit_endereco_cep", m),
            },
        },
        "document": {
            "number": _leaf(field_values["nMDF"], "ident_numero", m),
            "series": _leaf(field_values["serie"], "ident_serie", m),
            "issue_date": _leaf(field_values["dhEmi"], "data_emissao", m),
            "access_key": _leaf(field_values["chave_acesso"], "chave_acesso", m),
            "environment": _leaf("homologacao", "__no_bbox__", m),
        },
        "transport": {
            "modal": _leaf("aereo", "__no_bbox__", m),
            "aircraft_registration": _leaf(field_values["aircraft"], "aeronave_matricula", m),
            "flight_number": _leaf(field_values["n_voo"], "aeronave_voo", m),
        },
        "cargo": {
            "value": _leaf(
                f"{field_values['v_carga']:.2f}", "v_carga", m, raw_value=field_values["v_carga"]
            ),
        },
        "linked_documents": [
            {"access_key": _leaf(field_values["chave_nfe_vinculada"], "chave_nfe_vinculada", m)}
        ],
    }


def build_kie_danfse(field_values: dict, field_id_to_element: dict = None) -> dict:
    m = field_id_to_element
    return {
        "provider": {
            "cnpj": _leaf(field_values["emit_cnpj"], "emit_cnpj", m),
            "name": _leaf(field_values["emit_xNome"], "emit_xNome", m),
            "municipality": _leaf(field_values["municipality_name"], "municipio", m),
        },
        "document": {
            "number": _leaf(field_values["nNFSe"], "ident_numero", m),
            "issue_date": _leaf(field_values["dhEmi"], "data_emissao", m),
            "access_key": _leaf(field_values["key_nfse"], "chave_nfse", m),
            "environment": _leaf("homologacao", "__no_bbox__", m),
        },
        "service": {
            "code": _leaf(field_values["cTribNac"], "servico_codigo", m),
            "description": _leaf(field_values["xDescServ"], "servico_descricao", m),
            "value": _leaf(
                f"{field_values['vServ']:.2f}", "valor_servico", m, raw_value=field_values["vServ"]
            ),
        },
    }


def build_kie_dacce(field_values: dict, field_id_to_element: dict = None) -> dict:
    m = field_id_to_element
    emitente = field_values["emitente"]
    return {
        "issuer": {
            "name": _leaf(emitente["nome"], "emitente_nome", m),
            "municipality": _leaf(emitente["cidade"], "emitente_cidade", m),
            "uf": _leaf(emitente["uf"], "emitente_uf", m),
            "phone": _leaf(emitente["fone"], "emitente_fone", m),
        },
        "event": {
            "related_access_key": _leaf(field_values["chave_nfe"], "chave_nfe", m),
            "author_cnpj": _leaf(field_values["autor_cnpj"], "autor_cnpj", m),
            "recipient_cnpj": _leaf(field_values["dest_cnpj"], "dest_cnpj", m),
            "event_date": _leaf(field_values["dh_evento"], "data_evento", m),
            "correction_text": _leaf(field_values["xcorrecao"], "xcorrecao", m),
            "protocol": _leaf(field_values["n_prot"], "n_prot", m),
        },
    }
