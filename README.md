# Generate Synthetic Brazil Documents

Fork of [BrazilFiscalReport](https://github.com/Engenere/BrazilFiscalReport) repurposed as the rendering backend for a **synthetic data generator** of Brazilian auxiliary fiscal documents — DANFE (NF-e), DACTE (CT-e), DAMDFE (MDF-e), DANFSE (NFS-e) and DACCe (carta de correção da NF-e).

This is a research fork for a master's project: instead of turning a *real* SEFAZ XML into a PDF, the goal is to fabricate realistic-but-fake field values, assemble a valid XML from them, and reuse these same PDF renderers to produce synthetic training documents (eventually with per-field bounding-box/label annotations for document-extraction/OCR model training). The synthetic-data generation and annotation layers are being built on top of the renderers below; see the plan history for the roadmap.

## Rendering backend (unchanged from upstream)

Every renderer takes a raw XML string and produces a PDF:

```python
from brazilfiscalreport.danfe import Danfe

with open("nfe.xml", "r", encoding="utf8") as file:
    xml_content = file.read()

danfe = Danfe(xml=xml_content)
danfe.output("danfe.pdf")
```

The same pattern works for every document type — import the matching class (`Dacte`, `Damdfe`, `Danfse`, `DaCCe`), pass the XML and call `.output()`. Each renderer also accepts an optional `Config` object (e.g. `DanfeConfig`) for logo, margins, fonts, decimal precision, watermark, etc. — see the docstrings/dataclasses in each `brazilfiscalreport/<doctype>/config.py`.

## Development

```bash
pip install -e .
pip install pytest pytest-cov
pytest
```

## License

Licensed under LGPL-3.0, inherited from the upstream [BrazilFiscalReport](https://github.com/Engenere/BrazilFiscalReport) project — see [LICENSE](LICENSE).
