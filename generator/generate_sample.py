"""Script de PoC: gera N DANFEs sintéticos ponta-a-ponta e grava os artefatos
seguindo a convenção de pastas do PLANO_GERADOR.md (secao 2) — sem bbox real
ainda (ver generator/labels/kie.py e "Questões em aberto" #1 do plano).

Uso: python -m generator.generate_sample --count 5 --out dataset_dev --seed 0
"""

import argparse
import json
from pathlib import Path

from generator.danfe import generate_danfe
from generator.labels.kie import build_kie_danfe
from generator.labels.layout import build_label
from brazilfiscalreport.danfe import Danfe


def generate_one(seed: int, out_dir: Path) -> dict:
    xml_str, field_values = generate_danfe(seed=seed)

    danfe = Danfe(xml=xml_str)
    sample_id = f"danfe_dev_{seed:08d}"

    xml_dir = out_dir / "xml"
    pdf_dir = out_dir / "pdfs"
    labels_dir = out_dir / "labels"
    for d in (xml_dir, pdf_dir, labels_dir):
        d.mkdir(parents=True, exist_ok=True)

    xml_path = xml_dir / f"{sample_id}.xml"
    pdf_path = pdf_dir / f"{sample_id}.pdf"
    label_path = labels_dir / f"{sample_id}.json"

    xml_path.write_text(xml_str, encoding="utf8")
    danfe.output(str(pdf_path))

    source = {
        "xml_path": str(xml_path.relative_to(out_dir)),
        "pdf_path": str(pdf_path.relative_to(out_dir)),
        "fixture_template": "tpl_001",
        "generation_seed": seed,
    }
    # Extração pós-renderização (sem tocar brazilfiscalreport/), ver
    # generator/labels/layout.py e PLANO_GERADOR.md, Questões em aberto #1.
    label = build_label(pdf_path, field_values, doc_type="DANFE", doc_id=sample_id, source=source)
    label["kie"] = build_kie_danfe(field_values, label.pop("field_id_to_element"))

    label_path.write_text(json.dumps(label, ensure_ascii=False, indent=2), encoding="utf8")
    return label


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=5)
    parser.add_argument("--out", type=Path, default=Path("dataset_dev"))
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    for i in range(args.count):
        seed = args.seed + i
        label = generate_one(seed, args.out)
        print(f"[{i + 1}/{args.count}] {label['doc_id']} — {label['kie']['issuer']['name']['value']}")


if __name__ == "__main__":
    main()
