"""Modelos pydantic de validação (PLANO_GERADOR.md secao 4/15).

Escopo desta rodada: o `LabelRecord` (esquema canônico, uniforme entre os 5
tipos — secao 7) e o `ManifestRow` são validados via pydantic de verdade.
Um `FieldValues` pydantic MODEL por tipo de documento (5 modelos distintos,
um por doctype, dado que os campos diferem bastante entre DANFE/DACTE/etc.)
fica como follow-up explícito — por ora, `validate_field_values` faz
checagens estruturais leves (não substitui os 5 modelos completos, mas
pega os erros mais comuns: dict vazio, XML vazio).
"""

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class BBox(BaseModel):
    x: float
    y: float
    w: float
    h: float
    unit: Literal["mm"] = "mm"


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
    doc_type: Literal["DANFE", "DACTE", "DAMDFE", "DANFSE", "DACCE"]
    schema_version: str
    source: dict
    pages: list[Page]
    elements: list[Element]
    layout: dict
    ocr: dict
    kie: dict
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
        if value is None:
            errors.append(f"{doctype}: campo {key!r} e None")
    return errors
