# Carimbo de recebimento

Carimbo de conferência/recebimento sobreposto à nota, com data e rubrica à caneta. Três estilos: `blue_recebemos`, `classic_em_de` e `status_box` (PAGO/CONFERIDO/LANÇADO/LIQUIDADO). Aparece no preset `stamps_only` (e `pos_and_stamp`), colocado na área livre do layout.

## Como gerar

```bash
# no dataset completo (o efeito é sorteado por amostra):
python -m pipeline.cli generate --doctype danfe --count 20 --seed 42 --out dataset
# só este exemplo (determinístico):
python examples/make_effect_examples.py
```

```python
from augmentation.pipeline import augment_document
from pipeline.registry import DOCTYPES

spec = DOCTYPES["danfe"]
img_aug, label, meta = augment_document(
    image, label, field_values, seed=2026,
    artifact_preset="stamps_only", scan_mode="clean_digital", angle_deg=0.0,
    context=spec.augment_context(field_values),
)
```

## Antes e depois

| antes | depois |
|---|---|
| ![antes](effects/carimbo_recebimento/antes.jpg) | ![depois](effects/carimbo_recebimento/depois.jpg) |

Os três estilos:

| blue_recebemos | classic_em_de | status_box |
|---|---|---|
| ![](effects/carimbo_recebimento/estilo_blue_recebemos.jpg) | ![](effects/carimbo_recebimento/estilo_classic_em_de.jpg) | ![](effects/carimbo_recebimento/estilo_status_box.jpg) |

## O que sai

Trecho de `labels/<id>.json` (`layout.special_objects`), copiado da saída real:

```json
{
  "preset": "stamps_only",
  "seed": 2026,
  "augmentation": {
    "seed": 2026,
    "angle_deg": 0.0,
    "scan_mode": "clean_digital",
    "special_objects_added": [
      "stamp",
      "signature"
    ],
    "boxes_valid": true
  },
  "special_objects": [
    {
      "type": "stamp",
      "subtype": "receipt_stamp",
      "page": 1,
      "bbox": {
        "x": 136.847,
        "y": 252.231,
        "w": 50.77,
        "h": 28.385,
        "unit": "mm"
      },
      "field_id": null,
      "text": [
        "RECEBEMOS",
        "25/07/23",
        "SERVIÇOS DE MACHADO MEI"
      ]
    },
    {
      "type": "signature",
      "page": 1,
      "bbox": {
        "x": 101.539,
        "y": 11.077,
        "w": 40.385,
        "h": 16.846,
        "unit": "mm"
      },
      "field_id": null
    }
  ]
}
```
