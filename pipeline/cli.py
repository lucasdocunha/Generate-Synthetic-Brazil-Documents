"""CLI do gerador (PLANO_GERADOR.md secao 4.5).

    python -m pipeline.cli generate --doctype danfe --count 100 --workers 4
    python -m pipeline.cli generate --all --count 100
    python -m pipeline.cli validate --doctype danfe
    python -m pipeline.cli stats --doctype danfe
"""

from pathlib import Path
from typing import Optional

import typer

from pipeline.config import RunConfig
from pipeline.registry import DOCTYPES

app = typer.Typer()


@app.command()
def generate(
    doctype: Optional[str] = typer.Option(None, help="danfe|dacte|damdfe|danfse|dacce"),
    all: bool = typer.Option(False, "--all", help="gera os 5 tipos"),
    count: int = 100,
    seed: int = 42,
    workers: int = 4,
    out: str = "dataset",
):
    from pipeline.batch import run_batch, run_batch_all

    cfg = RunConfig(count=count, seed=seed, workers=workers, out_dir=out)
    if all:
        run_batch_all(cfg)
    elif doctype:
        if doctype not in DOCTYPES:
            typer.echo(f"Tipo desconhecido: {doctype}. Opções: {list(DOCTYPES)}")
            raise typer.Exit(1)
        run_batch(doctype, cfg)
    else:
        typer.echo("Especifique --doctype <tipo> ou --all")
        raise typer.Exit(1)


@app.command()
def validate(doctype: str, out: str = "dataset"):
    from validation.auditor import audit_doctype

    result = audit_doctype(Path(out), doctype)
    typer.echo(f"{doctype}: {result['valid']}/{result['total']} válidos")
    if result["schema_errors"]:
        typer.echo(f"  {len(result['schema_errors'])} erros de esquema")
    if result["missing_files"]:
        typer.echo(f"  {len(result['missing_files'])} referências de arquivo ausentes")


@app.command()
def stats(doctype: str, out: str = "dataset"):
    import pyarrow.parquet as pq

    path = Path(out) / doctype / "manifest.parquet"
    if not path.exists():
        typer.echo(f"Nenhum manifesto encontrado em {path}")
        raise typer.Exit(1)
    table = pq.read_table(path).to_pylist()
    n = len(table)
    avg_match = sum(r["match_rate"] for r in table) / n if n else 0.0
    typer.echo(f"{doctype}: {n} amostras, match_rate médio = {avg_match:.3f}")


if __name__ == "__main__":
    app()
