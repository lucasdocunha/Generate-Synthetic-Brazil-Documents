# Generate Synthetic Brazil Documents

Gerador de documentos fiscais sintéticos brasileiros (DANFE, Consulta Web Portal NF-e, DACTE, DAMDFE, DANFSE, DACCE e NFS-e Legado) com XML válido, PDF vetorial, imagens degradadas e anotações de layout/KIE com reprojeção geométrica de bounding boxes.

## 1. Instalação

```bash
uv sync
# ou
pip install -e .
```

## 2. Geração em Grande Lote (CLI)

O pipeline distribui automaticamente a geração em múltiplos processos (`--workers`), divide em `train/val/test` (80/10/10), aplica variações de ERP/layout/ruído por amostra e salva checkpoints por arquivo (rodar novamente o mesmo comando retoma de onde parou sem regerar amostras prontas).

### Gerar lote de DANFE (NF-e tradicional)
```bash
python -m pipeline.cli generate \
  --doctype danfe \
  --count 10000 \
  --workers 8 \
  --seed 42 \
  --cnpj-alnum-ratio 0.3 \
  --out dataset
```

### Gerar lote de Consultas do Portal da NF-e (Clássica + SVRS)
```bash
python -m pipeline.cli generate \
  --doctype nfe_portal \
  --count 5000 \
  --workers 8 \
  --seed 42 \
  --cnpj-alnum-ratio 0.3 \
  --out dataset
```

### Gerar todos os tipos registrados de uma vez
Tipos incluídos: `danfe`, `nfe_portal`, `dacte`, `damdfe`, `danfse`, `dacce`.
```bash
python -m pipeline.cli generate --all --count 5000 --workers 8 --out dataset
```

### Validar e inspecionar o lote gerado
```bash
python -m pipeline.cli validate --doctype danfe --out dataset
python -m pipeline.cli stats --doctype danfe --out dataset
```

## 3. Personalização da NF-e (Python API)

### 3.1. DANFE: Presets de ERP, Orientação Horizontal e CNPJ Alfanumérico

No modo padrão (`erp_preset=None`), cada `seed` sorteia automaticamente entre os presets de ERP, fontes, estilos de tabela, logos e orientação. Para fixar um preset específico:

```python
from brazilfiscalreport.danfe import Danfe
from generator.danfe import generate_danfe, render_kwargs

# Presets disponíveis:
# - "linx_autosystem": Times, coluna de combustível ANP, canhoto no topo, crédito Linx
# - "xpert": Helvetica, coluna VALOR LÍQ., crédito Xpert no emitente e rodapé
# - "galago": Courier, colunas V. DESC. + VALOR LÍQ., canhoto no rodapé
# - "minimal_open": Helvetica, tabela de itens sem linha inferior (OPEN_BOTTOM)
# - "classic_landscape": DANFE horizontal (paisagem) com canhoto lateral esquerdo
xml_str, fv = generate_danfe(
    seed=100,
    cnpj_alnum_ratio=0.5,       # 0.0 = apenas numérico | 1.0 = 100% alfanumérico (IN RFB 2.229/2024)
    erp_preset="classic_landscape",
)

cfg_kwargs = render_kwargs(fv)
pdf = Danfe(xml=xml_str, **cfg_kwargs)
pdf.output("danfe_custom.pdf")
```

Para controle fino manual sobre o `DanfeConfig`:

```python
from brazilfiscalreport.danfe import (
    Danfe,
    DanfeConfig,
    FontFamily,
    InvoicePosition,
    ProductColumnsPreset,
    ProductTableStyle,
)
from generator.branding.logo_factory import generate_company_logo

logo_bytes = generate_company_logo(
    "Comercial Exemplo LTDA",
    seed=42,
    style="fuel_shield",  # "badge_seal" | "modern_corporate" | "fuel_shield" | "minimal_monogram"
)

config = DanfeConfig(
    orientation="P",                                  # "P" (retrato) ou "L" (paisagem/horizontal)
    font_family=FontFamily.TIMES,                     # HELVETICA, TIMES ou COURIER
    invoice_position=InvoicePosition.TOP,             # TOP, BOTTOM ou LEFT_LANDSCAPE
    product_table_style=ProductTableStyle.FULL_FRAME, # FULL_FRAME, FULL_VERTICAL_GRID ou OPEN_BOTTOM
    product_columns_preset=ProductColumnsPreset.FUEL_ANP, # STANDARD, FUEL_ANP ou DISCOUNT_LIQUID
    logo=logo_bytes,
    erp_footer_credit="LINX SISTEMAS - AutoSystem 3.2.5",
    show_real_recipient_in_homologation=True,
)

pdf = Danfe(xml=xml_str, config=config)
pdf.output("danfe_manual.pdf")
```

### 3.2. Consulta Web do Portal da NF-e (`nfe_portal`)

```python
from brazilfiscalreport.portal_nfe import PortalNfe
from generator.portal_nfe import generate_portal_nfe

# variant: "classic_fazenda" (Portal Nacional) ou "modern_svrs" (Portal SVRS em cards)
xml_str, fv = generate_portal_nfe(seed=42, cnpj_alnum_ratio=0.3, variant="modern_svrs")
pdf = PortalNfe(xml=xml_str, variant=fv["_portal_variant"])
pdf.output("portal_nfe.pdf")
```

### 3.3. Carimbos, Comprovantes POS, Ruídos de Scanner e Reprojeção de BBoxes

A função `augment_document` aplica artefatos físicos, inclinação e digitalização sobre a imagem rasterizada e atualiza `label` com as coordenadas reprojetadas:

```python
import cv2
from augmentation.pipeline import augment_document
from generator.labels.layout import build_label, flatten_danfe_fields
from rasterization.raster import rasterize

images = rasterize("danfe_custom.pdf", dpi=200)
label = build_label(
    "danfe_custom.pdf",
    fv,
    doc_type="DANFE",
    doc_id="danfe_0001",
    source={"generation_seed": 100},
    flatten_fn=flatten_danfe_fields,
)

# scan_mode: "clean_digital" | "color_scan" | "bw_binarized_scan" | "heavy_degraded"
# artifact_preset: "none" | "stamps_only" | "pos_receipt" | "pos_and_stamp" | "scratches"
img_aug, label_reprojected, aug_meta = augment_document(
    images[0],
    label,
    fv,
    seed=100,
    scan_mode="bw_binarized_scan",
    artifact_preset="pos_and_stamp",
    tilt_deg=-2.5,  # graus de inclinação; None sorteia automaticamente conforme scan_mode
)

cv2.imwrite("danfe_scanned.png", cv2.cvtColor(img_aug, cv2.COLOR_RGB2BGR))
```

## 4. Estrutura de Saída do Dataset

Para cada `doctype`, o lote grava em `<out_dir>/<doctype>/`:

- `xml/<shard>/<doc_id>.xml`: XML fiscal completo.
- `pdfs/<shard>/<doc_id>.pdf`: PDF vetorial original.
- `images/<shard>/<doc_id>.png`: imagem com artefatos físicos, carimbos, inclinação e ruído de scanner.
- `images/<shard>/<doc_id>_geo.png`: variante com distorção geométrica adicional (perspectiva/curvatura).
- `labels/<shard>/<doc_id>.json`:
  - `pages[].elements[]`: texto extraído com `bbox` (`[x0, y0, x1, y1]` em mm reprojetado após rotação) e `obb_points` (4 vértices exatos da caixa rotacionada).
  - `layout.special_objects[]`: bounding boxes de `barcode`, `stamp` (carimbos), `signature` (rubricas) e `pos_receipt` (comprovantes de cartão).
  - `kie`: entidades chave-valor anotadas com `tax_id_type` (`cnpj_numeric`, `cnpj_alnum`, `cpf`).
- `meta/<shard>/<doc_id>.json`: metadados do sorteio (preset de ERP, modo de scanner, ângulo de rotação, formato de CNPJ).
- `manifest.parquet`: índice tabular consolidado do lote.
