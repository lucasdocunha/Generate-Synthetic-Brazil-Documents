"""Registro central de tipos de documento (PLANO_GERADOR.md secao 14): para
adicionar um 6º tipo, basta um adaptador `generator/<tipo>.py` + funções de
label em `generator/labels/` + uma entrada aqui — nenhum outro código do
`pipeline/` precisa mudar.
"""

import inspect

from renderers.dacce import DaCCe
from renderers.dacte import Dacte
from renderers.damdfe import Damdfe
from renderers.danfe import Danfe
from renderers.danfse import Danfse
from renderers.nfse_legado import NfseLegado
from renderers.portal_nfe import PortalNfe
from generator.dacce import generate_dacce
from generator.dacte import generate_dacte
from generator.damdfe import generate_damdfe
from generator.danfe import generate_danfe
from generator.danfe import render_kwargs as danfe_render_kwargs
from generator.danfse import generate_danfse
from generator.labels import kie, layout
from generator.nfse_legado import generate_nfse_legado
from generator.portal_nfe import generate_portal_nfe
from generator.portal_nfe import render_kwargs as portal_nfe_render_kwargs


def nfse_legado_render_kwargs(field_values):
    # o envelope Ginfes não traz razão social do prestador nem o nome do município
    return {
        "razao_social_prestador": field_values["razao_social_prestador"],
        "municipality_name": field_values["municipality_name"],
        "city_layout": field_values.get("_render", {}).get("city_layout", "ginfes"),
    }


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
        render_kwargs_fn=None,
    ):
        from augmentation.context import CONTEXT_FNS

        # field_values -> contexto de augmentation (emitente, data, valor, canhoto)
        self.augment_context_fn = CONTEXT_FNS[name]
        self.name = name
        self.generate_fn = generate_fn
        self.render_class = render_class
        self.flatten_fn = flatten_fn
        self.kie_builder = kie_builder
        self.has_vector_barcode = has_vector_barcode
        self.needs_emitente_dict = needs_emitente_dict
        # field_values -> kwargs extras do renderer (ex.: DanfeConfig sorteado)
        self.render_kwargs_fn = render_kwargs_fn

    def html_spec(self):
        """Spec de HTML do tipo (htmlgen), ou None se ainda não suportado."""
        from htmlgen.registry import html_specs

        return html_specs().get(self.name)

    def augment_context(self, field_values):
        return self.augment_context_fn(field_values)

    def generate(self, seed, **opts):
        """Retorna (xml_str, field_values, render_kwargs).

        `opts` (ex.: cnpj_alnum_ratio) só são repassados aos geradores que
        aceitam o parâmetro — os demais ignoram silenciosamente.
        """
        params = inspect.signature(self.generate_fn).parameters
        kwargs = {k: v for k, v in opts.items() if k in params}
        if self.needs_emitente_dict:
            xml_str, emitente, field_values = self.generate_fn(seed=seed, **kwargs)
            return xml_str, field_values, {"emitente": emitente}
        xml_str, field_values = self.generate_fn(seed=seed, **kwargs)
        extra = self.render_kwargs_fn(field_values) if self.render_kwargs_fn else {}
        return xml_str, field_values, extra

    def render(self, xml_str, render_kwargs):
        return self.render_class(xml=xml_str, **render_kwargs)


DOCTYPES = {
    "danfe": DoctypeSpec(
        "danfe", generate_danfe, Danfe, layout.flatten_danfe_fields, kie.build_kie_danfe,
        has_vector_barcode=True, render_kwargs_fn=danfe_render_kwargs,
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
    "nfe_portal": DoctypeSpec(
        "nfe_portal", generate_portal_nfe, PortalNfe, layout.flatten_portal_nfe_fields, kie.build_kie_danfe,
        has_vector_barcode=False, render_kwargs_fn=portal_nfe_render_kwargs,
    ),
    "nfse_legado": DoctypeSpec(
        "nfse_legado", generate_nfse_legado, NfseLegado, layout.flatten_nfse_legado_fields,
        kie.build_kie_nfse_legado, has_vector_barcode=False, render_kwargs_fn=nfse_legado_render_kwargs,
    ),
}
