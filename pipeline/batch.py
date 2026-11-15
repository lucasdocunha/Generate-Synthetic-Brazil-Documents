"""Driver de lote (PLANO_GERADOR.md secao 3.2): paralelismo via joblib,
resume = rodar o mesmo comando de novo (o check de "pronto" já está em
`export.writer.is_sample_done`, chamado dentro de `pipeline.single.generate_one`).
"""

from pathlib import Path

from joblib import Parallel, delayed

from export.manifest import write_manifest
from pipeline.single import generate_one


def _splits_for_count(count: int, split_ratios: dict):
    items = list(split_ratios.items())
    counts = {}
    remaining = count
    for name, ratio in items[:-1]:
        n = round(count * ratio)
        counts[name] = n
        remaining -= n
    counts[items[-1][0]] = max(remaining, 0)
    return counts


def run_batch(doctype: str, cfg, log=print):
    out_dir = Path(cfg.out_dir)
    split_counts = _splits_for_count(cfg.count, cfg.split_ratios)

    rows = []
    for split, n in split_counts.items():
        if n <= 0:
            continue
        log(f"[{doctype}/{split}] gerando {n} amostras...")
        results = Parallel(n_jobs=cfg.workers)(
            delayed(generate_one)(
                doctype, split, i, cfg.seed, out_dir, cfg.dpi_options, cfg.generate_geometric_variant,
                gen_opts={"cnpj_alnum_ratio": cfg.cnpj_alnum_ratio},
            )
            for i in range(n)
        )
        ok = [r for r in results if r is not None]
        failed = len(results) - len(ok)
        log(f"[{doctype}/{split}] {len(ok)}/{n} ok, {failed} falhas (ver .failed_samples.jsonl)")
        rows.extend(ok)

    write_manifest(out_dir, doctype, rows)
    return rows


def run_batch_all(cfg, log=print):
    all_rows = {}
    for doctype in cfg.doctypes:
        all_rows[doctype] = run_batch(doctype, cfg, log=log)
    return all_rows
