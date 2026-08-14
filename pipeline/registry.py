"""Registro central de tipos de documento (PLANO_GERADOR.md secao 14): para
adicionar um 6º tipo, basta um adaptador `generator/<tipo>.py` + funções de
label em `generator/labels/` + uma entrada aqui — nenhum outro código do
`pipeline/` precisa mudar.
"""

from brazilfiscalreport.dacce import DaCCe
from brazilfiscalreport.dacte import Dacte
from brazilfiscalreport.damdfe import Damdfe
from brazilfiscalreport.danfe import Danfe
from brazilfiscalreport.danfse import Danfse

from generator.dacce import generate_dacce
from generator.dacte import generate_dacte
from generator.damdfe import generate_damdfe
from generator.danfe import generate_danfe
from generator.danfse import generate_danfse
from generator.labels import kie, layout


class DoctypeSpec:
    def __init__(
        self,
        name,
        generate_fn,
        render_class,
        flatten_fn,
        kie_builder,
        has_vector_barcode,
        needs_emitente_dict=False,
    ):
        self.name = name
        self.generate_fn = generate_fn
        self.render_class = render_class
        self.flatten_fn = flatten_fn
        self.kie_builder = kie_builder
        self.has_vector_barcode = has_vector_barcode
        self.needs_emitente_dict = needs_emitente_dict

    def generate(self, seed):
        """Retorna (xml_str, field_values, render_kwargs)."""
        if self.needs_emitente_dict:
            xml_str, emitente, field_values = self.generate_fn(seed=seed)
            return xml_str, field_values, {"emitente": emitente}
        xml_str, field_values = self.generate_fn(seed=seed)
        return xml_str, field_values, {}

    def render(self, xml_str, render_kwargs):
        return self.render_class(xml=xml_str, **render_kwargs)


DOCTYPES = {
    "danfe": DoctypeSpec(
        "danfe", generate_danfe, Danfe, layout.flatten_danfe_fields, kie.build_kie_danfe,
        has_vector_barcode=True,
    ),
    "dacte": DoctypeSpec(
        "dacte", generate_dacte, Dacte, layout.flatten_dacte_fields, kie.build_kie_dacte,
        has_vector_barcode=False,
    ),
    "damdfe": DoctypeSpec(
        "damdfe", generate_damdfe, Damdfe, layout.flatten_damdfe_fields, kie.build_kie_damdfe,
        has_vector_barcode=False,
    ),
    "danfse": DoctypeSpec(
        "danfse", generate_danfse, Danfse, layout.flatten_danfse_fields, kie.build_kie_danfse,
        has_vector_barcode=False,
    ),
    "dacce": DoctypeSpec(
        "dacce", generate_dacce, DaCCe, layout.flatten_dacce_fields, kie.build_kie_dacce,
        has_vector_barcode=True, needs_emitente_dict=True,
    ),
}
