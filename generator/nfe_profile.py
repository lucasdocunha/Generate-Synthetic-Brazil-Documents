"""Perfil estrutural de uma NF-e sintética (eixo de diversidade do XML).

Cada amostra sorteia um `NfeProfile` com pesos de
`generator/schemas/danfe.yaml` (seção `profiles`). O adaptador
`generator/danfe.py` usa o perfil para podar o template maximal tpl_002 e
para escolher grupos de imposto, partes opcionais e a config do renderer.
`overrides` permite forçar qualquer eixo (testes, geração estratificada).
"""

import random
from dataclasses import asdict, dataclass, fields
from pathlib import Path

import yaml

_SCHEMA_PATH = Path(__file__).resolve().parent / "schemas" / "danfe.yaml"
with open(_SCHEMA_PATH, encoding="utf8") as _f:
    WEIGHTS = yaml.safe_load(_f)["profiles"]

CRT_BY_REGIME = {"normal": "3", "simples": "1", "mei": "4"}


@dataclass
class NfeProfile:
    regime: str = "normal"
    dest_pj: bool = False
    transporta: bool = False
    veiculo: bool = False
    cobr: bool = False
    retirada: bool = False
    entrega: bool = False
    frete_seguro_outros: bool = False
    desconto: bool = False
    ipi_tributado: bool = False
    special_items: bool = False
    issqn: bool = False
    ibs_cbs: bool = False
    inf_ad_prod_rate: float = 0.0
    inf_cpl: bool = False
    nfe_proc: bool = False
    n_items: int = 1
    landscape: bool = False
    receipt_bottom: bool = False
    font_courier: bool = False
    font_helvetica: bool = False
    font_big: bool = False
    display_pis_cofins: bool = False
    duplicates_only: bool = False
    decimals: int = 4
    has_logo: bool = False
    erp_style: str = "standard"
    vertical_block_labels: bool = False

    @property
    def crt(self) -> str:
        return CRT_BY_REGIME[self.regime]

    def to_dict(self) -> dict:
        return asdict(self)


def _bern(rng, p):
    return rng.random() < p


def sample_profile(rng: random.Random, overrides: dict = None) -> NfeProfile:
    w = WEIGHTS
    regimes = list(w["regime"].keys())
    regime = rng.choices(regimes, weights=[w["regime"][r] for r in regimes], k=1)[0]

    buckets = w["items"]
    bucket = rng.choices(buckets, weights=[b["weight"] for b in buckets], k=1)[0]
    n_items = rng.randint(*bucket["range"])

    r = w["render"]
    transporta = _bern(rng, w["transporta"])
    erp_map = r.get("erp_styles", {"standard": 1.0})
    erp_keys = list(erp_map.keys())
    erp_style = rng.choices(erp_keys, weights=[erp_map[k] for k in erp_keys], k=1)[0]
    landscape = (erp_style == "classic_landscape") or _bern(rng, r["landscape"])
    font_helvetica = (
        True
        if erp_style in ("linx_autosystem", "galago")
        else (False if erp_style in ("xpert", "minimal_open") else _bern(rng, r.get("font_helvetica", 0.45)))
    )
    vertical_block_labels = erp_style in ("classic_landscape", "galago") or (landscape and rng.random() < 0.6)
    p = NfeProfile(
        regime=regime,
        dest_pj=_bern(rng, w["dest_pj"]),
        transporta=transporta,
        veiculo=transporta and _bern(rng, w["veiculo"]),
        cobr=_bern(rng, w["cobr"]),
        retirada=_bern(rng, w["retirada"]),
        entrega=_bern(rng, w["entrega"]),
        frete_seguro_outros=_bern(rng, w["frete_seguro_outros"]),
        desconto=_bern(rng, w["desconto"]),
        ipi_tributado=regime == "normal" and _bern(rng, w["ipi_tributado"]),
        special_items=_bern(rng, w["special_items"]),
        issqn=(erp_style == "galago") or _bern(rng, w["issqn"]),
        ibs_cbs=_bern(rng, w["ibs_cbs"]),
        inf_ad_prod_rate=w["inf_ad_prod"],
        inf_cpl=_bern(rng, w["inf_cpl"]),
        nfe_proc=_bern(rng, w["nfe_proc"]),
        n_items=n_items,
        landscape=landscape,
        receipt_bottom=(not landscape) and _bern(rng, r["receipt_bottom"]),
        font_courier=_bern(rng, r["font_courier"]),
        font_helvetica=font_helvetica,
        font_big=_bern(rng, r["font_big"]),
        display_pis_cofins=_bern(rng, r["display_pis_cofins"]),
        duplicates_only=_bern(rng, r["duplicates_only"]),
        decimals=2 if _bern(rng, r["decimals_2"]) else 4,
        has_logo=(erp_style == "galago") or _bern(rng, r.get("has_logo", 0.65)),
        erp_style=erp_style,
        vertical_block_labels=vertical_block_labels,
    )
    if overrides:
        valid = {f.name for f in fields(NfeProfile)}
        unknown = set(overrides) - valid
        if unknown:
            raise ValueError(f"overrides desconhecidos: {sorted(unknown)}")
        for k, v in overrides.items():
            setattr(p, k, v)
    return p
