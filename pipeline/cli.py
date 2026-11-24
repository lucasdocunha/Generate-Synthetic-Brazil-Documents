"""CLI do gerador (PLANO_GERADOR.md secao 4.5).

    python -m pipeline.cli generate --doctype danfe --count 100 --workers 4
    python -m pipeline.cli generate --all --count 100 --html
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
    doctype: Optional[str] = typer.Option(None, help="danfe|nfe_portal|dacte|damdfe|danfse|dacce|nfse_legado"),
    all: bool = typer.Option(False, "--all", help="gera todos os tipos registrados"),
    count: int = 100,
    seed: int = 42,
    workers: int = 4,
    out: str = "dataset",
    cnpj_alnum_ratio: float = typer.Option(
        0.3, help="fração de CNPJs alfanuméricos (IN RFB 2.229/2024), 0.0-1.0"
    ),
    html: bool = typer.Option(False, "--html", help="gera também HTML/Markdown (html_clean, md, html_visible, md_visible)"),
    image_source: str = typer.Option("lib_pdf", help="lib_pdf (PDF real da lib) | html (render do próprio HTML)"),
):
    from pipeline.batch import run_batch, run_batch_all

    cfg = RunConfig(
        count=count, seed=seed, workers=workers, out_dir=out, cnpj_alnum_ratio=cnpj_alnum_ratio,
        html=html, image_source=image_source,
    )
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
