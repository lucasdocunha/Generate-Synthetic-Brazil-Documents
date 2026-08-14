"""Configuração de execução (PLANO_GERADOR.md secao 2, `config/` — não
confundir com `generator/schemas/`, que é "o que é um DANFE", não "quanto
gerar nesta rodada")."""

from dataclasses import dataclass, field


@dataclass
class RunConfig:
    doctypes: list = field(default_factory=lambda: ["danfe", "dacte", "damdfe", "danfse", "dacce"])
    count: int = 100
    seed: int = 42
    workers: int = 4
    out_dir: str = "dataset"
    split_ratios: dict = field(default_factory=lambda: {"train": 0.8, "val": 0.1, "test": 0.1})
    dpi_options: list = field(default_factory=lambda: [150, 200, 300])
    generate_geometric_variant: bool = True
