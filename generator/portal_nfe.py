"""Adaptador para a Consulta Web do Portal da Nota Fiscal Eletrônica (`nfe_portal`).

Reaproveita `generate_danfe` (mesmo XML de NF-e 4.00, mesmas garantias de
consistência e de CNPJ alfanumérico) e sorteia entre as variantes:
- `classic_fazenda` (ref. PDF 6324935 pág. 2)
- `modern_svrs` (ref. PDF 7438757 págs. 1-3)
"""

import random

from generator import fake_data
from generator.danfe import generate_danfe


def generate_portal_nfe(
    seed=None,
    variant=None,
    cnpj_alnum_ratio=fake_data.DEFAULT_CNPJ_ALNUM_RATIO,
):
    rng = random.Random(seed)
    chosen_variant = variant or rng.choice(["classic_fazenda", "modern_svrs"])
    n_items = rng.randint(1, 3)
    xml_str, fv = generate_danfe(
        seed=seed,
        num_items=n_items,
        profile_overrides={"nfe_proc": True, "decimals": 4},
        cnpj_alnum_ratio=cnpj_alnum_ratio,
    )
    fv["_render"] = {
        "portal_variant": chosen_variant,
        "decimals": 4,
    }
    return xml_str, fv


def render_kwargs(field_values: dict) -> dict:
    spec = field_values.get("_render") or {}
    return {"variant": spec.get("portal_variant", "modern_svrs")}
