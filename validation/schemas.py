"""Modelos pydantic de validação (PLANO_GERADOR.md secao 4/15).

Escopo desta rodada: o `LabelRecord` (esquema canônico, uniforme entre os 5
tipos — secao 7) e o `ManifestRow` são validados via pydantic de verdade.
Um `FieldValues` pydantic MODEL por tipo de documento (5 modelos distintos,
um por doctype, dado que os campos diferem bastante entre DANFE/DACTE/etc.)
fica como follow-up explícito — por ora, `validate_field_values` faz
checagens estruturais leves (não substitui os 5 modelos completos, mas
pega os erros mais comuns: dict vazio, XML vazio).
"""

import re
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class BBox(BaseModel):
    x: float
    y: float
    w: float
    h: float
    unit: Literal["mm"] = "mm"
    obb_points: Optional[list[list[float]]] = None


class Element(BaseModel):
    element_id: str
    field_ids: list[str] = Field(default_factory=list)
    role: Literal["content", "unlabeled", "label", "decoration"]
    page: int
    bbox: BBox
    text: str


class Page(BaseModel):
    page_number: int
    size_mm: Optional[dict] = None


class ExtractionStats(BaseModel):
    fields_total: int
    fields_matched_to_bbox: int
    match_rate: float


class LabelRecord(BaseModel):
    doc_id: str
    doc_type: Literal["DANFE", "DACTE", "DAMDFE", "DANFSE", "DACCE", "NFE_PORTAL", "NFSE_LEGADO"]
    schema_version: str
    source: dict
    pages: list[Page]
    elements: list[Element]
    layout: dict
    ocr: dict
    kie: dict = {}  # opcional: tipos sem KIE (ex.: NFS-e legada) deixam vazio
    extraction_stats: ExtractionStats

    @field_validator("pages")
    @classmethod
    def _at_least_one_page(cls, v):
        if not v:
            raise ValueError("documento sem nenhuma pagina")
        return v


class ManifestRow(BaseModel):
    doc_id: str
    doctype: str
    split: str
    seed: int
    match_rate: float
    n_pages: int


def validate_field_values(doctype: str, field_values: dict) -> list:
    """Checagem estrutural leve (nao substitui um pydantic model por tipo,
    ver nota no topo do arquivo). Retorna lista de erros (vazia = ok)."""
    errors = []
    if not field_values:
        errors.append(f"{doctype}: field_values vazio")
    for key, value in field_values.items():
        if value is None and key not in _OPTIONAL_NONE_KEYS:
            errors.append(f"{doctype}: campo {key!r} e None")
    if doctype in ("danfe", "nfe_portal"):
        errors.extend(validate_danfe_consistency(field_values))
    elif doctype == "dacte":
        for role in ("emit", "rem", "exped", "receb", "dest"):
            _check_doc(errors, f"{role}.cnpj", field_values.get(role, {}).get("cnpj"), "cnpj", doctype)
        if not ACCESS_KEY_RE.match(field_values.get("chave_acesso", "")):
            errors.append("dacte: chave_acesso inválida")
    elif doctype == "damdfe":
        _check_doc(errors, "emit_cnpj", field_values.get("emit_cnpj"), "cnpj", doctype)
        if not ACCESS_KEY_RE.match(field_values.get("chave_acesso", "")):
            errors.append("damdfe: chave_acesso inválida")
    elif doctype == "danfse":
        _check_doc(errors, "emit_cnpj", field_values.get("emit_cnpj"), "cnpj", doctype)
    elif doctype == "dacce":
        _check_doc(errors, "autor_cnpj", field_values.get("autor_cnpj"), "cnpj", doctype)
        _check_doc(errors, "dest_cnpj", field_values.get("dest_cnpj"), "cnpj", doctype)
        if not ACCESS_KEY_RE.match(field_values.get("chave_nfe", "")):
            errors.append("dacce: chave_nfe inválida")
    return errors


# blocos opcionais da NF-e: None significa "ausente neste perfil", não erro
_OPTIONAL_NONE_KEYS = {"retirada", "entrega", "transp", "protocolo"}


# --- Checagens de formato/consistência (NF-e) -------------------------------

# CNPJ (numérico ou alfanumérico, IN RFB 2.229/2024): 12 posições [0-9A-Z] + 2 DVs numéricos
CNPJ_RE = re.compile(r"^[0-9A-Z]{12}[0-9]{2}$")
CPF_RE = re.compile(r"^[0-9]{11}$")
# Chave: cUF(2) AAMM(4) CNPJ(14, pode ter letras) mod(2) serie(3) nNF(9) tpEmis(1) cNF(8) cDV(1)
ACCESS_KEY_RE = re.compile(r"^[0-9]{6}[0-9A-Z]{12}[0-9]{26}$")


def _check_doc(errors, label, doc, doc_type, doctype="danfe"):
    regex = CPF_RE if doc_type == "cpf" else CNPJ_RE
    if not doc or not regex.match(doc):
        errors.append(f"{doctype}: {label} com formato inválido para {doc_type}: {doc!r}")


def validate_danfe_consistency(fv: dict) -> list:
    errors = []
    _check_doc(errors, "emit_cnpj", fv.get("emit_cnpj"), "cnpj")
    if "dest_doc" in fv:
        _check_doc(errors, "dest_doc", fv["dest_doc"], fv.get("dest_doc_type", "cpf"))
    for role in ("retirada", "entrega", "transp"):
        part = fv.get(role)
        if part:
            _check_doc(errors, f"{role}.doc", part["doc"], part["doc_type"])

    chave = fv.get("chave_acesso", "")
    if not ACCESS_KEY_RE.match(chave):
        errors.append(f"danfe: chave de acesso com formato inválido: {chave!r}")
    elif chave[6:20] != fv.get("emit_cnpj"):
        errors.append("danfe: CNPJ embutido na chave difere do emitente")

    t = fv.get("totals")
    if t:
        expected = round(t["vProd"] - t["vDesc"] + t["vST"] + t["vFrete"] + t["vSeg"]
                         + t["vOutro"] + t["vIPI"] + t.get("vServ", 0.0), 2)
        if abs(expected - t["vNF"]) > 0.011:
            errors.append(f"danfe: vNF {t['vNF']} != fórmula {expected}")
    cobr = fv.get("cobr")
    if cobr and cobr["dups"]:
        s = round(sum(float(d["vDup"]) for d in cobr["dups"]), 2)
        if abs(s - fv["total_vNF"]) > 0.011:
            errors.append(f"danfe: soma das duplicatas {s} != vNF {fv['total_vNF']}")
    return errors
