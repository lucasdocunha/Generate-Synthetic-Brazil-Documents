"""Gera os exemplos de cada efeito de degradação em examples/effects/<efeito>/.

    python examples/make_effect_examples.py

Documento-base: DANFE de página única (seed fixa). Cada efeito é forçado com
`augment_document(..., artifact_preset=..., scan_mode=..., angle_deg=...)` e seed
fixa, então a saída é determinística. Grava `antes.jpg`, `depois.jpg` e os
trechos (`label.json`, `html_visible.html`, `md_visible.md`) usados nos .md.
"""

from __future__ import annotations

import json
import random
import sys
import tempfile
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PIL import Image  # noqa: E402

from augmentation.pipeline import augment_document, augment_geometric_variant  # noqa: E402
from augmentation.stamps import apply_scratches_and_scan_borders  # noqa: E402
from generator.labels.layout import build_label  # noqa: E402
from pipeline.registry import DOCTYPES  # noqa: E402
from rasterization.raster import rasterize  # noqa: E402

OUT = ROOT / "examples" / "effects"
SEED = 2026
DOC_SEED = 11
DPI = 110
WIDTH = 820


def save(img: Image.Image, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    img = img.convert("RGB")
    img.resize((WIDTH, round(img.height * WIDTH / img.width)), Image.LANCZOS).save(path, quality=78, optimize=True)


def base_document():
    """DANFE de página única + label (como no pipeline) + contexto de augmentation."""
    spec = DOCTYPES["danfe"]
    for s in range(DOC_SEED, DOC_SEED + 60):
        xml, fv, kw = spec.generate(s)
        pdf = bytes(spec.render(xml, kw).output())
        images = rasterize(pdf, dpi=DPI)
        if len(images) == 1:
            break
    with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp:
        tmp.write(pdf)
        tmp.flush()
        label = build_label(tmp.name, fv, "DANFE", "danfe_exemplo", {"generation_seed": s},
                            spec.flatten_fn, spec.has_vector_barcode)
    label.pop("field_id_to_element", None)
    return spec, xml, fv, pdf, images[0], label


def objs(label, types):
    return [o for o in label["layout"]["special_objects"] if o["type"] in types]


def dump(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf8")


def main():
    spec, xml, fv, pdf, image, label = base_document()
    ctx = spec.augment_context(fv)

    def run(effect, preset, scan="clean_digital", angle=0.0, seed=SEED):
        img, lbl, meta = augment_document(image, label, fv, seed=seed, artifact_preset=preset,
                                          scan_mode=scan, angle_deg=angle, context=ctx)
        return img, lbl, meta

    # 1-4: carimbos, POS, assinatura (presets) ---------------------------------
    cases = {
        "carimbo_recebimento": ("stamps_only", {"stamp"}),
        "carimbo_cnpj": ("stamp_and_cnpj", {"stamp"}),
        "comprovante_pos": ("pos_overlay", {"pos_receipt"}),
        "assinatura": ("signature_and_scratches", {"signature"}),
    }
    for name, (preset, types) in cases.items():
        for seed in range(SEED, SEED + 40):  # primeira seed em que o objeto aparece
            img, lbl, meta = run(name, preset, seed=seed)
            if objs(lbl, types):
                break
        save(image, OUT / name / "antes.jpg")
        save(img, OUT / name / "depois.jpg")
        dump(OUT / name / "label.json", {"preset": preset, "seed": seed, "augmentation": meta,
                                         "special_objects": objs(lbl, {"stamp", "pos_receipt", "signature"})})

    # estilos do carimbo de recebimento (um por estilo)
    from augmentation.stamps import render_receipt_stamp

    for st in ("blue_recebemos", "classic_em_de", "status_box"):
        s_img = render_receipt_stamp(random.Random(SEED), ctx["name"], ctx["date_br"], style=st)
        bg = Image.new("RGB", s_img.size, "white")
        bg.paste(s_img, mask=s_img.split()[3])
        bg.save(OUT / "carimbo_recebimento" / f"estilo_{st}.jpg", quality=85)

    # 5: riscos, dobra e bordas -------------------------------------------------
    scratched = apply_scratches_and_scan_borders(image, random.Random(SEED), True, True, True)
    save(image, OUT / "riscos_dobra_bordas" / "antes.jpg")
    save(scratched, OUT / "riscos_dobra_bordas" / "depois.jpg")
    for nome, kw in (("so_riscos", dict(add_pen_scratches=True, add_scan_borders=False, add_fold_or_streak=False)),
                     ("so_bordas", dict(add_pen_scratches=False, add_scan_borders=True, add_fold_or_streak=False)),
                     ("so_dobra", dict(add_pen_scratches=False, add_scan_borders=False, add_fold_or_streak=True))):
        save(apply_scratches_and_scan_borders(image, random.Random(SEED), **kw),
             OUT / "riscos_dobra_bordas" / f"{nome}.jpg")

    # 6: inclinação com reprojeção das caixas -----------------------------------
    img, lbl, meta = run("inclinacao", "none", angle=3.0)
    save(image, OUT / "inclinacao" / "antes.jpg")
    save(img, OUT / "inclinacao" / "depois.jpg")
    el0 = next(e for e in label["elements"] if e["page"] == 1)
    el1 = next(e for e in lbl["elements"] if e["element_id"] == el0["element_id"])
    dump(OUT / "inclinacao" / "label.json", {"angle_deg": 3.0, "antes": {"text": el0["text"], "bbox": el0["bbox"]},
                                             "depois": {"text": el1["text"], "bbox": el1["bbox"]}})

    # 7: modos de scanner ---------------------------------------------------------
    save(image, OUT / "modos_scanner" / "antes.jpg")
    for mode in ("clean_digital", "color_scan", "bw_binarized_scan"):
        img, _lbl, _m = run("modos_scanner", "none", scan=mode)
        save(img, OUT / "modos_scanner" / f"{mode}.jpg")

    # 8: variante geométrica ------------------------------------------------------
    g_img, g_meta = augment_geometric_variant(image, seed=SEED)
    save(image, OUT / "variante_geometrica" / "antes.jpg")
    save(g_img, OUT / "variante_geometrica" / "depois.jpg")
    dump(OUT / "variante_geometrica" / "meta.json", g_meta)

    # 9: oclusão no HTML (POS + assinatura) --------------------------------------
    from htmlgen.convert import to_clean_html, to_markdown
    from htmlgen.occlusion import apply_degradation
    from htmlgen.render import get_renderer

    for seed in range(SEED, SEED + 60):
        img, lbl, meta = run("oclusao_html", "pos_overlay", seed=seed)
        if objs(lbl, {"pos_receipt"}):
            break
    res = spec.html_spec().render(xml, fv, DOC_SEED, get_renderer(), lib_pdf=pdf, need_pdf=False)
    vis_full, report = apply_degradation(res.html_full, lbl)
    clean = to_clean_html(res.html_full)
    visible = to_clean_html(vis_full)
    d = OUT / "oclusao_html"
    save(image, d / "antes.jpg")
    save(img, d / "depois.jpg")
    (d / "html_clean.html").write_text(clean, encoding="utf8")
    (d / "html_visible.html").write_text(visible, encoding="utf8")
    (d / "md_visible.md").write_text(to_markdown(vis_full, "table"), encoding="utf8")
    dump(d / "relatorio.json", report)
    print("exemplos gravados em", OUT)


if __name__ == "__main__":
    main()
