"""Convenção de nome/sharding (PLANO_GERADOR.md secao 2.2): evita diretórios
com dezenas de milhares de arquivos, agrupando a cada 10.000 ids."""

SHARD_SIZE = 10_000


def sample_id(doctype: str, split: str, index: int) -> str:
    return f"{doctype}_{split}_{index:08d}"


def shard_dir(index: int) -> str:
    return f"{(index // SHARD_SIZE):04d}"
