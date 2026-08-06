"""Extração de bounding boxes/labels a partir do PDF já renderizado, via
PyMuPDF — sem tocar em `brazilfiscalreport/` (PLANO_GERADOR.md, "Questões em
aberto" #1, revisitada: em vez de instrumentar `xFPDF`, extraímos geometria
de texto/imagem/vetor de fora, do PDF finalizado, e casamos com os valores
fake já conhecidos de `field_values`).

Fluxo:
1. `extract_spans(pdf_path)` — todo span de texto de cada página, via
   `page.get_text("dict")`, que já agrupa em blocos/linhas/spans na ordem de
   leitura natural do MuPDF (inclusive a tabela de produtos, linha por
   linha — verificado empiricamente, ver PLANO_GERADOR.md).
2. `find_barcode_bbox(page)` — heurística: código de barras (Code128 via
   python-barcode) é desenhado como vetores (retângulos finos), não como
   imagem raster, então não aparece em `get_image_info()`; agrupamos os
   retângulos finos e altos num envelope.
3. `match_fields(spans, field_values)` — casa cada valor fake conhecido
   com o span mais curto que o contém (normalizado, sem pontuação/case),
   preferindo o span mais específico sobre blobs de texto concatenados
   (ex.: a "faixa de recibo" do DANFE, que junta várias informações numa
   só chamada de desenho).
4. `build_label(...)` — monta `elements[]`/`layout`/`ocr` do label
   canônico (PLANO_GERADOR.md secao 7).
"""

import re
import unicodedata

import fitz

_PT_TO_MM = 25.4 / 72.0


def _pt_to_mm(value: float) -> float:
    return round(value * _PT_TO_MM, 3)


def _normalize(s: str) -> str:
    s = unicodedata.normalize("NFKC", str(s))
    return re.sub(r"[^\w]", "", s, flags=re.UNICODE).casefold()


def extract_spans(pdf_path):
    """Retorna lista de dicts {page, bbox_pt, text} — um por span de texto,
    na ordem retornada pelo MuPDF (aproximadamente ordem de leitura)."""
    doc = fitz.open(pdf_path)
    spans = []
    for page_index in range(doc.page_count):
        page = doc[page_index]
        text_dict = page.get_text("dict")
        for block in text_dict["blocks"]:
            if block.get("type") != 0:  # 0 = texto, 1 = imagem
                continue
            for line in block["lines"]:
                for span in line["spans"]:
                    text = span["text"].strip()
                    if not text:
                        continue
                    spans.append(
                        {
                            "page": page_index + 1,
                            "bbox_pt": span["bbox"],
                            "text": text,
                        }
                    )
    doc.close()
    return spans


def find_barcode_bbox(pdf_path, page_number=1):
    """Heurística: agrupa retângulos finos e altos (barras de um Code128
    desenhado como vetor, não como imagem raster) num envelope único.
    Só funciona bem quando há UM código de barras na página (caso do DANFE).
    """
    doc = fitz.open(pdf_path)
    page = doc[page_number - 1]
    bars = []
    for d in page.get_drawings():
        r = d["rect"]
        if d.get("fill") and r.width < 3 and r.height > 5:
            bars.append(r)
    doc.close()
    if not bars:
        return None
    return {
        "page": page_number,
        "bbox_pt": (
            min(r.x0 for r in bars),
            min(r.y0 for r in bars),
            max(r.x1 for r in bars),
            max(r.y1 for r in bars),
        ),
    }


def extract_image_bboxes(pdf_path):
    """QR codes/logos (imagens raster de verdade, via self.image()) — ao
    contrário do código de barras, aparecem direto em get_image_info()."""
    doc = fitz.open(pdf_path)
    images = []
    for page_index in range(doc.page_count):
        page = doc[page_index]
        for info in page.get_image_info():
            images.append({"page": page_index + 1, "bbox_pt": info["bbox"]})
    doc.close()
    return images


def flatten_danfe_fields(field_values: dict) -> dict:
    """Achata field_values num dict {field_id: valor_bruto_como_string},
    incluindo uma versão 'exibível' para datas (dd/mm/aaaa), já que o
    casamento é feito por normalização (remove pontuação), não por
    reprodução exata da formatação do renderer.
    """
    flat = {}
    e = field_values["emit_endereco"]
    d = field_values["dest_endereco"]

    flat.update(
        {
            "emit_cnpj_cpf": field_values["emit_cnpj"],
            "emit_xNome": field_values["emit_xNome"],
            "emit_xFant": field_values["emit_xFant"],
            "emit_IE": field_values["emit_IE"],
            "emit_endereco_logradouro": e["street"],
            "emit_endereco_bairro": e["neighborhood"],
            "emit_endereco_municipio": e["municipality_name"],
            "emit_endereco_uf": e["uf"],
            "emit_endereco_cep": e["cep"],
            "emit_fone": field_values["emit_fone"],
            "dest_cnpj_cpf": field_values["dest_cpf"],
            "dest_xNome": field_values["dest_xNome"],
            "dest_endereco_logradouro": d["street"],
            "dest_endereco_bairro": d["neighborhood"],
            "dest_endereco_municipio": d["municipality_name"],
            "dest_endereco_uf": d["uf"],
            "dest_endereco_cep": d["cep"],
            "dest_fone": field_values["dest_fone"],
            "dest_email": field_values["dest_email"],
            "chave_acesso": field_values["chave_acesso"],
            "ident_numero": field_values["nNF"],
            "ident_serie": field_values["serie"],
            "natureza_operacao": field_values["natOp"],
            "total_vnf": f"{field_values['total_vNF']:.2f}",
            "total_vicms": f"{field_values['total_vICMS']:.2f}",
        }
    )

    dh_emi = field_values["dhEmi"]
    date_part = dh_emi.split("T")[0]
    yyyy, mm, dd = date_part.split("-")
    flat["data_emissao"] = f"{dd}/{mm}/{yyyy}"

    for idx, item in enumerate(field_values["items"], start=1):
        prefix = f"item_{idx}_"
        flat[prefix + "codigo"] = item["cProd"]
        flat[prefix + "descricao"] = item["xProd"]
        flat[prefix + "ncm"] = item["NCM"]
        flat[prefix + "cfop"] = item["CFOP"]
        # qCom/vUnCom são armazenados no XML com muitas casas decimais (o
        # schema da NF-e pede isso), mas o DANFE exibe arredondado em
        # `quantity_precision`/`price_precision` (4 casas por padrão) — usar
        # o valor bruto de muitas casas como chave de busca falha (é mais
        # longo que o texto exibido, então nunca é "contido" nele). Usa-se
        # aqui o float já calculado (item["_qtd"]/["_preco_unit"])
        # arredondado na mesma precisão exibida pelo renderer.
        flat[prefix + "qtd"] = f"{item['_qtd']:.4f}"
        flat[prefix + "vunit"] = f"{item['_preco_unit']:.4f}"
        flat[prefix + "vtotal"] = item["vProd"]
        flat[prefix + "vicms"] = item["vICMS"]

    return flat


def _iso_to_br_date(iso_dt: str) -> str:
    date_part = iso_dt.split("T")[0]
    yyyy, mm, dd = date_part.split("-")
    return f"{dd}/{mm}/{yyyy}"


def flatten_dacte_fields(field_values: dict) -> dict:
    flat = {}
    for role in ("emit", "rem", "exped", "receb", "dest"):
        party = field_values[role]
        e = party["endereco"]
        flat[f"{role}_cnpj"] = party["cnpj"]
        flat[f"{role}_xNome"] = party["xNome"]
        flat[f"{role}_fone"] = party["fone"]
        flat[f"{role}_endereco_logradouro"] = e["street"]
        flat[f"{role}_endereco_bairro"] = e["neighborhood"]
        flat[f"{role}_endereco_municipio"] = e["municipality_name"]
        flat[f"{role}_endereco_uf"] = e["uf"]
        flat[f"{role}_endereco_cep"] = e["cep"]
        if party["email"]:
            flat[f"{role}_email"] = party["email"]

    flat.update(
        {
            "chave_acesso": field_values["chave_acesso"],
            "ident_serie": field_values["serie"],
            "ident_numero": field_values["nCT"],
            "natureza_operacao": field_values["natOp"],
            "data_emissao": _iso_to_br_date(field_values["dhEmi"]),
            "v_frete": f"{field_values['v_frete']:.2f}",
            "v_icms": f"{field_values['v_icms']:.2f}",
            "v_carga": f"{field_values['v_carga']:.2f}",
            "descricao_carga": field_values["descricao_carga"],
        }
    )
    return flat


def flatten_damdfe_fields(field_values: dict) -> dict:
    e = field_values["emit_endereco"]
    return {
        "emit_cnpj": field_values["emit_cnpj"],
        "emit_xNome": field_values["emit_xNome"],
        "emit_xFant": field_values["emit_xFant"],
        "emit_IE": field_values["emit_IE"],
        "emit_endereco_logradouro": e["street"],
        "emit_endereco_bairro": e["neighborhood"],
        "emit_endereco_municipio": e["municipality_name"],
        "emit_endereco_uf": e["uf"],
        "emit_endereco_cep": e["cep"],
        "emit_fone": field_values["emit_fone"],
        "emit_email": field_values["emit_email"],
        "chave_acesso": field_values["chave_acesso"],
        "ident_serie": field_values["serie"],
        "ident_numero": field_values["nMDF"],
        "data_emissao": _iso_to_br_date(field_values["dhEmi"]),
        "aeronave_matricula": field_values["aircraft"],
        "aeronave_voo": field_values["n_voo"],
        "v_carga": f"{field_values['v_carga']:.2f}",
        "chave_nfe_vinculada": field_values["chave_nfe_vinculada"],
    }


def flatten_danfse_fields(field_values: dict) -> dict:
    return {
        "emit_cnpj": field_values["emit_cnpj"],
        "emit_xNome": field_values["emit_xNome"],
        "municipio": field_values["municipality_name"],
        "ident_numero": field_values["nNFSe"],
        "data_emissao": _iso_to_br_date(field_values["dhEmi"]),
        "servico_codigo": field_values["cTribNac"],
        "servico_descricao": field_values["xDescServ"],
        "valor_servico": f"{field_values['vServ']:.2f}",
        "chave_nfse": field_values["key_nfse"],
    }


def flatten_dacce_fields(field_values: dict) -> dict:
    emitente = field_values["emitente"]
    return {
        "autor_cnpj": field_values["autor_cnpj"],
        "dest_cnpj": field_values["dest_cnpj"],
        "chave_nfe": field_values["chave_nfe"],
        "data_evento": _iso_to_br_date(field_values["dh_evento"]),
        "xcorrecao": field_values["xcorrecao"],
        "n_prot": field_values["n_prot"],
        "emitente_nome": emitente["nome"],
        "emitente_bairro": emitente["bairro"],
        "emitente_cidade": emitente["cidade"],
        "emitente_uf": emitente["uf"],
        "emitente_fone": emitente["fone"],
    }


def match_fields(spans, flat_field_values):
    """Para cada campo, acha o span mais curto cujo texto normalizado
    contém o valor normalizado do campo. Retorna {field_id: span_index}
    (índice em `spans`), só para os campos que deram match."""
    normalized_spans = [(_normalize(s["text"]), s["text"]) for s in spans]

    matches = {}
    for field_id, value in flat_field_values.items():
        norm_value = _normalize(value)
        if not norm_value:
            continue
        best_idx = None
        best_len = None
        for idx, (norm_span, _raw) in enumerate(normalized_spans):
            if norm_value in norm_span:
                if best_len is None or len(norm_span) < best_len:
                    best_idx = idx
                    best_len = len(norm_span)
        if best_idx is not None:
            matches[field_id] = best_idx
    return matches


def build_label(
    pdf_path,
    field_values: dict,
    doc_type: str,
    doc_id: str,
    source: dict,
    flatten_fn,
    has_vector_barcode: bool = False,
):
    """Monta o label canônico (PLANO_GERADOR.md secao 7) com elements[]
    reais (bbox em mm) casados por valor, mais um bloco `layout` mínimo
    (código de barras/QR) e `ocr.full_text` via extração nativa do MuPDF.

    `flatten_fn(field_values) -> {field_id: valor}` é específico de cada
    tipo de documento (ver flatten_<tipo>_fields abaixo); o resto desta
    função é genérico e reaproveitado pelos 5 tipos.
    """
    doc = fitz.open(pdf_path)
    pages = [
        {
            "page_number": i + 1,
            "size_mm": {
                "w": _pt_to_mm(doc[i].rect.width),
                "h": _pt_to_mm(doc[i].rect.height),
            },
        }
        for i in range(doc.page_count)
    ]
    ocr_pages = [
        {"page_number": i + 1, "text": doc[i].get_text("text")} for i in range(doc.page_count)
    ]
    doc.close()

    spans = extract_spans(pdf_path)
    flat = flatten_fn(field_values)
    matches = match_fields(spans, flat)

    span_to_field = {}
    for field_id, span_idx in matches.items():
        span_to_field.setdefault(span_idx, []).append(field_id)

    elements = []
    for idx, span in enumerate(spans):
        x0, y0, x1, y1 = span["bbox_pt"]
        field_ids = span_to_field.get(idx, [])
        elements.append(
            {
                "element_id": f"e{idx:05d}",
                "field_ids": field_ids,
                "role": "content" if field_ids else "unlabeled",
                "page": span["page"],
                "bbox": {
                    "x": _pt_to_mm(x0),
                    "y": _pt_to_mm(y0),
                    "w": _pt_to_mm(x1 - x0),
                    "h": _pt_to_mm(y1 - y0),
                    "unit": "mm",
                },
                "text": span["text"],
            }
        )

    special_objects = []
    if has_vector_barcode:
        barcode = find_barcode_bbox(pdf_path, page_number=1)
        if barcode:
            x0, y0, x1, y1 = barcode["bbox_pt"]
            special_objects.append(
                {
                    "type": "barcode",
                    "page": barcode["page"],
                    "bbox": {
                        "x": _pt_to_mm(x0),
                        "y": _pt_to_mm(y0),
                        "w": _pt_to_mm(x1 - x0),
                        "h": _pt_to_mm(y1 - y0),
                        "unit": "mm",
                    },
                    "field_id": "chave_acesso",
                }
            )

    for img in extract_image_bboxes(pdf_path):
        x0, y0, x1, y1 = img["bbox_pt"]
        special_objects.append(
            {
                "type": "qrcode_or_logo",
                "page": img["page"],
                "bbox": {
                    "x": _pt_to_mm(x0),
                    "y": _pt_to_mm(y0),
                    "w": _pt_to_mm(x1 - x0),
                    "h": _pt_to_mm(y1 - y0),
                    "unit": "mm",
                },
                "field_id": None,
            }
        )

    field_id_to_element = {}
    for field_id, span_idx in matches.items():
        field_id_to_element[field_id] = f"e{span_idx:05d}"

    n_matched = len(matches)
    n_fields = len(flat)

    return {
        "doc_id": doc_id,
        "doc_type": doc_type,
        "schema_version": "0.2-poc-postproc-bbox",
        "source": source,
        "pages": pages,
        "elements": elements,
        "layout": {"special_objects": special_objects},
        "ocr": {
            "full_text": "\n".join(p["text"] for p in ocr_pages),
            "pages": ocr_pages,
        },
        "field_id_to_element": field_id_to_element,
        "extraction_stats": {
            "fields_total": n_fields,
            "fields_matched_to_bbox": n_matched,
            "match_rate": round(n_matched / n_fields, 3) if n_fields else 0.0,
        },
    }
