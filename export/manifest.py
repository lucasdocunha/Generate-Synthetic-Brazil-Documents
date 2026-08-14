"""Manifesto Parquet por tipo de documento (PLANO_GERADOR.md secao 2.2/4.7):
índice rápido para análise sem abrir cada label individualmente.

Simplificação de concorrência: os workers do batch driver (pipeline/batch.py)
NÃO escrevem no manifesto diretamente — cada um só retorna sua linha, e o
processo principal (onde joblib.Parallel já coleta os resultados) acumula e
grava o parquet uma vez, evitando qualquer escrita concorrente em arquivo.
"""

from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq


def write_manifest(out_dir: Path, doctype: str, rows: list):
    if not rows:
        return None
    table = pa.Table.from_pylist(rows)
    path = out_dir / doctype / "manifest.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, path)
    return path


def append_manifest(out_dir: Path, doctype: str, new_rows: list):
    """Lê o parquet existente (se houver), concatena e regrava — usado ao
    retomar um lote (PLANO_GERADOR.md secao 3.2)."""
    path = out_dir / doctype / "manifest.parquet"
    existing = []
    if path.exists():
        existing = pq.read_table(path).to_pylist()
    write_manifest(out_dir, doctype, existing + new_rows)
    return path
