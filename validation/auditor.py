"""Auditor de dataset já gerado (PLANO_GERADOR.md secao 4.4): revalida cada
label.json contra o esquema pydantic e confere integridade referencial
(os arquivos de imagem/pdf/xml apontados realmente existem)."""

import json
from pathlib import Path

from pydantic import ValidationError

from validation.schemas import LabelRecord


def audit_doctype(out_dir: Path, doctype: str) -> dict:
    base = out_dir / doctype
    labels_dir = base / "labels"
    results = {"total": 0, "valid": 0, "schema_errors": [], "missing_files": []}

    if not labels_dir.exists():
        return results

    for shard_dir in sorted(labels_dir.iterdir()):
        if not shard_dir.is_dir():
            continue
        for label_path in sorted(shard_dir.glob("*.json")):
            results["total"] += 1
            try:
                data = json.loads(label_path.read_text(encoding="utf8"))
                record = LabelRecord(**data)
            except (json.JSONDecodeError, ValidationError) as e:
                results["schema_errors"].append((str(label_path), str(e)))
                continue

            for ref_key in ("xml_path", "pdf_path", "html_path", "md_path", "html_visible_path"):
                ref = record.source.get(ref_key)
                if ref and not (out_dir / doctype / ref).exists():
                    results["missing_files"].append((str(label_path), ref_key, ref))

            # imagens (limpas por página e degradada)
            stem = label_path.stem
            shard = label_path.parent.name
            for rel in (f"images/{shard}/{stem}_p1.png", f"images_aug/{shard}/{stem}.png"):
                if not (out_dir / doctype / rel).exists():
                    results["missing_files"].append((str(label_path), "image", rel))

            if not any(m[0] == str(label_path) for m in results["missing_files"]):
                results["valid"] += 1

    return results


def audit_all(out_dir: Path, doctypes: list) -> dict:
    return {d: audit_doctype(out_dir, d) for d in doctypes}
