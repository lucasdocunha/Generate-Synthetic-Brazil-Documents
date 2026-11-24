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


def _tax_id_type(doc: str, doc_type: str) -> str:
    """'cpf' | 'cnpj' | 'cnpj_alnum' (IN RFB 2.229/2024)."""
    if doc_type == "cpf":
        return "cpf"
    return "cnpj_alnum" if any(c.isalpha() for c in doc) else "cnpj"


def _money_leaf(value: float, key, m):
    return _leaf(f"{value:.2f}", key if value else "__no_bbox__", m, raw_value=value)


def _kie_location(part, prefix, m):
    if not part:
        return None
    end = part["endereco"]
    return {
        "tax_id": _leaf(part["doc"], f"{prefix}_cnpj_cpf", m),
        "tax_id_type": _tax_id_type(part["doc"], part["doc_type"]),
        "name": _leaf(part["xNome"], f"{prefix}_xNome", m),
        "address": {
            "street": _leaf(end["street"], f"{prefix}_endereco_logradouro", m),
            "number": _leaf(end["number"], "__no_bbox__", m),
            "neighborhood": _leaf(end["neighborhood"], f"{prefix}_endereco_bairro", m),
            "municipality": _leaf(end["municipality_name"], f"{prefix}_endereco_municipio", m),
            "uf": _leaf(end["uf"], "__no_bbox__", m),
            "cep": _leaf(end["cep"], f"{prefix}_endereco_cep", m),
        },
    }


def build_kie_danfe(field_values: dict, field_id_to_element: dict = None) -> dict:
    """KIE da NF-e (schema 0.3): destinatário com `tax_id` + `tax_id_type`
    (cpf | cnpj | cnpj_alnum) no lugar de `cpf`; nós opcionais `carrier`,
    `billing`, `pickup`, `delivery`, `authorization_protocol` são None quando
    o bloco não existe no documento."""
    m = field_id_to_element
    emit_end = field_values["emit_endereco"]
    dest_end = field_values["dest_endereco"]
    totals = field_values.get("totals", {})
    dest_doc = field_values.get("dest_doc", field_values.get("dest_cpf"))
    dest_doc_type = field_values.get("dest_doc_type", "cpf")

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
                "cst_csosn": _leaf(f"{item.get('orig', '')}{item.get('CST', '')}", p + "cst", m),
                "unit": _leaf(item["uCom"], p + "unidade", m),
                "quantity": _leaf(item["qCom"], p + "qtd", m, raw_value=item["_qtd"]),
                "unit_price": _leaf(item["vUnCom"], p + "vunit", m, raw_value=item["_preco_unit"]),
                "total_price": _leaf(item["vProd"], p + "vtotal", m, raw_value=item["_v_prod"]),
                "icms_value": _leaf(item["vICMS"], p + "vicms", m,
                                    raw_value=item.get("_vICMS", item.get("_v_icms"))),
                "ipi_value": _leaf(item.get("vIPI", "0.00"), "__no_bbox__", m),
                "additional_info": item.get("infAdProd") or None,
            }
        )

    transp = field_values.get("transp")
    carrier = None
    if transp:
        carrier = {
            "freight_mode": transp["modFrete"],
            "tax_id": _leaf(transp["doc"], "transp_cnpj_cpf", m),
            "tax_id_type": _tax_id_type(transp["doc"], transp["doc_type"]),
            "name": _leaf(transp["xNome"], "transp_xNome", m),
            "state_registration": _leaf(transp["IE"], "transp_IE", m) if transp["IE"] else None,
            "address": _leaf(transp["xEnder"], "transp_xEnder", m),
            "municipality": _leaf(transp["xMun"], "transp_xMun", m),
            "vehicle_plate": _leaf(transp["veiculo"]["placa"], "transp_placa", m) if transp["veiculo"] else None,
            "volumes": {
                "quantity": _leaf(transp["vol"]["qVol"], "vol_qvol", m),
                "species": _leaf(transp["vol"]["esp"], "vol_especie", m),
                "gross_weight": _leaf(transp["vol"]["pesoB"], "vol_peso_bruto", m),
                "net_weight": _leaf(transp["vol"]["pesoL"], "vol_peso_liquido", m),
            },
        }

    cobr = field_values.get("cobr")
    billing = None
    if cobr and cobr["dups"]:
        billing = {
            "invoice_number": _leaf(cobr["nFat"], "fatura_numero", m),
            "installments": [
                {
                    "number": dup["nDup"],
                    "due_date": dup["dVenc"],
                    "value": dup["vDup"],
                    "bbox_ref": (m or {}).get(f"dup_{k}_numero_venc_valor"),
                }
                for k, dup in enumerate(cobr["dups"], start=1)
            ],
        }

    prot = field_values.get("protocolo")

    return {
        "issuer": {
            "cnpj": _leaf(field_values["emit_cnpj"], "emit_cnpj_cpf", m),
            "tax_id_type": _tax_id_type(field_values["emit_cnpj"], "cnpj"),
            "name": _leaf(field_values["emit_xNome"], "emit_xNome", m),
            "fantasy_name": _leaf(field_values["emit_xFant"], "emit_xFant", m),
            "state_registration": _leaf(field_values["emit_IE"], "emit_IE", m),
            "tax_regime_crt": field_values.get("_profile", {}).get("regime"),
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
            "tax_id": _leaf(dest_doc, "dest_cnpj_cpf", m),
            "tax_id_type": _tax_id_type(dest_doc, dest_doc_type),
            "name": _leaf(field_values["dest_xNome"], "dest_xNome", m),
            "state_registration": (
                _leaf(field_values["dest_IE"], "dest_IE", m) if field_values.get("dest_IE") else None
            ),
            "address": {
                "street": _leaf(dest_end["street"], "dest_endereco_logradouro", m),
                "number": _leaf(dest_end["number"], "dest_endereco_numero", m),
                "neighborhood": _leaf(dest_end["neighborhood"], "dest_endereco_bairro", m),
                "municipality": _leaf(dest_end["municipality_name"], "dest_endereco_municipio", m),
                "uf": _leaf(dest_end["uf"], "dest_endereco_uf", m),
                "cep": _leaf(dest_end["cep"], "dest_endereco_cep", m),
            },
        },
        "pickup": _kie_location(field_values.get("retirada"), "retirada", m),
        "delivery": _kie_location(field_values.get("entrega"), "entrega", m),
        "document": {
            "number": _leaf(field_values["nNF"], "ident_numero", m),
            "series": _leaf(field_values["serie"], "ident_serie", m),
            "issue_date": _leaf(field_values["dhEmi"], "data_emissao", m),
            "access_key": _leaf(field_values["chave_acesso"], "chave_acesso", m),
            "environment": _leaf("homologacao", "__no_bbox__", m),
            "nature_of_operation": _leaf(field_values["natOp"], "natureza_operacao", m),
            "authorization_protocol": _leaf(prot["nProt"], "protocolo_autorizacao", m) if prot else None,
        },
        "totals": {
            "total_value": _leaf(
                f"{field_values['total_vNF']:.2f}", "total_vnf", m, raw_value=field_values["total_vNF"]
            ),
            "products_value": _money_leaf(totals.get("vProd", field_values.get("total_vProd", 0.0)), "total_vprod", m),
            "icms_base": _money_leaf(totals.get("vBC", 0.0), "total_vbc", m),
            "icms_total": _money_leaf(field_values["total_vICMS"], "total_vicms", m),
            "icms_st_base": _money_leaf(totals.get("vBCST", 0.0), "total_vbcst", m),
            "icms_st_total": _money_leaf(totals.get("vST", 0.0), "total_vst", m),
            "ipi_total": _money_leaf(totals.get("vIPI", 0.0), "total_vipi", m),
            "discount": _money_leaf(totals.get("vDesc", 0.0), "total_vdesc", m),
            "freight": _money_leaf(totals.get("vFrete", 0.0), "total_vfrete", m),
            "insurance": _money_leaf(totals.get("vSeg", 0.0), "total_vseg", m),
            "other_expenses": _money_leaf(totals.get("vOutro", 0.0), "total_voutro", m),
            "approx_taxes": _money_leaf(totals.get("vTotTrib", 0.0), "total_vtottrib", m),
            "services_value": _money_leaf(totals.get("vServ", 0.0), "issqn_vserv", m),
            "iss_total": _money_leaf(totals.get("vISS", 0.0), "issqn_viss", m),
        },
        "carrier": carrier,
        "billing": billing,
        "items": items,
    }


def build_kie_dacte(field_values: dict, field_id_to_element: dict = None) -> dict:
    m = field_id_to_element

    def party(role):
        p = field_values[role]
        e = p["endereco"]
        return {
            "cnpj": _leaf(p["cnpj"], f"{role}_cnpj", m),
            "tax_id_type": _tax_id_type(p["cnpj"], "cnpj"),
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
            "tax_id_type": _tax_id_type(field_values["emit_cnpj"], "cnpj"),
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
            "tax_id_type": _tax_id_type(field_values["emit_cnpj"], "cnpj"),
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


def build_kie_nfse_legado(field_values: dict, field_id_to_element: dict = None) -> dict:
    m = field_id_to_element
    tomador = field_values["cpf_cnpj_tomador"]
    return {
        "provider": {
            "cnpj": _leaf(field_values["cnpj_prestador"], "prestador_cnpj", m),
            "tax_id_type": _tax_id_type(field_values["cnpj_prestador"], "cnpj"),
            "name": _leaf(field_values["razao_social_prestador"], "prestador_razao_social", m),
            "inscricao_municipal": _leaf(field_values["inscricao_municipal"], "prestador_inscricao_municipal", m),
            "municipality": _leaf(field_values["municipality_name"], "municipio", m),
        },
        "taker": {
            "document": _leaf(tomador, "tomador_documento", m),
            "tax_id_type": _tax_id_type(tomador, "cpf" if len(tomador) == 11 else "cnpj"),
            "name": _leaf(field_values["razao_social_tomador"], "tomador_razao_social", m),
        },
        "document": {
            "rps_number": _leaf(field_values["numero_rps"], "ident_numero", m),
            "batch_number": _leaf(str(field_values["numero_lote"]), "ident_lote", m),
            "issue_date": _leaf(field_values["dEmissao"], "data_emissao", m),
            "environment": _leaf("homologacao", "__no_bbox__", m),
        },
        "service": {
            "code": _leaf(field_values["item_lista_servico"], "servico_codigo", m),
            "description": _leaf(field_values["discriminacao"], "servico_descricao", m),
            "value": _leaf(
                f"{field_values['v_serv']:.2f}", "valor_servicos", m, raw_value=field_values["v_serv"]
            ),
            "iss_rate": _leaf(f"{field_values['aliquota']:.2f}", "aliquota", m, raw_value=field_values["aliquota"]),
            "iss_value": _leaf(
                f"{field_values['v_iss']:.2f}", "valor_iss", m, raw_value=field_values["v_iss"]
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
            "author_tax_id_type": _tax_id_type(field_values["autor_cnpj"], "cnpj"),
            "recipient_cnpj": _leaf(field_values["dest_cnpj"], "dest_cnpj", m),
            "recipient_tax_id_type": _tax_id_type(field_values["dest_cnpj"], "cnpj"),
            "event_date": _leaf(field_values["dh_evento"], "data_evento", m),
            "correction_text": _leaf(field_values["xcorrecao"], "xcorrecao", m),
            "protocol": _leaf(field_values["n_prot"], "n_prot", m),
        },
    }
