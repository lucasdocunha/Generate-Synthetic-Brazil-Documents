"""Specs de HTML por tipo de documento."""

from __future__ import annotations

PDF_DERIVED = ("dacte", "damdfe", "dacce", "danfse", "nfe_portal", "nfse_legado")


def html_specs() -> dict:
    from htmlgen.specs import danfe
    from htmlgen.specs.from_pdf import make_spec

    specs = {"danfe": danfe.SPEC}
    specs.update({n: make_spec(n) for n in PDF_DERIVED})
    return specs
