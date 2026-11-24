"""Escreve examples/<efeito>.md a partir da saída real de make_effect_examples.py."""
import json
from pathlib import Path

EX = Path(__file__).resolve().parent
FX = EX / "effects"


def j(p, keys=None):
    d = json.loads((FX / p).read_text("utf8"))
    return json.dumps(d, ensure_ascii=False, indent=2)


def head(p, n):
    return "\n".join((FX / p).read_text("utf8").splitlines()[:n])


def snippet_html(p, marker, before=2, after=8):
    lines = (FX / p).read_text("utf8").splitlines()
    i = next(k for k, l in enumerate(lines) if marker in l)
    return "\n".join(lines[max(0, i - before): i + after])


def page(name, title, what, cmd, outputs, extra=""):
    (EX / f"{name}.md").write_text(f"""# {title}

{what}

## Como gerar

```bash
# no dataset completo (o efeito é sorteado por amostra):
python -m pipeline.cli generate --doctype danfe --count 20 --seed 42 --out dataset
# só este exemplo (determinístico):
python examples/make_effect_examples.py
```

```python
{cmd}
```

## Antes e depois

| antes | depois |
|---|---|
| ![antes](effects/{name}/antes.jpg) | ![depois](effects/{name}/depois.jpg) |
{extra}
## O que sai

{outputs}
""", encoding="utf8")


PY_BASE = """from augmentation.pipeline import augment_document
from pipeline.registry import DOCTYPES

spec = DOCTYPES["danfe"]
img_aug, label, meta = augment_document(
    image, label, field_values, seed=2026,
    artifact_preset="{preset}", scan_mode="clean_digital", angle_deg=0.0,
    context=spec.augment_context(field_values),
)"""

lab = lambda n: f"Trecho de `labels/<id>.json` (`layout.special_objects`), copiado da saída real:\n\n```json\n{j(n + '/label.json')}\n```"

page("carimbo_recebimento", "Carimbo de recebimento",
     "Carimbo de conferência/recebimento sobreposto à nota, com data e rubrica à caneta. Três estilos: `blue_recebemos`, `classic_em_de` e `status_box` (PAGO/CONFERIDO/LANÇADO/LIQUIDADO). Aparece no preset `stamps_only` (e `pos_and_stamp`), colocado na área livre do layout.",
     PY_BASE.format(preset="stamps_only"), lab("carimbo_recebimento"),
     "\nOs três estilos:\n\n| blue_recebemos | classic_em_de | status_box |\n|---|---|---|\n| ![](effects/carimbo_recebimento/estilo_blue_recebemos.jpg) | ![](effects/carimbo_recebimento/estilo_classic_em_de.jpg) | ![](effects/carimbo_recebimento/estilo_status_box.jpg) |\n")
page("carimbo_cnpj", "Carimbo de CNPJ",
     "Carimbo societário com cantoneiras (CNPJ, razão social e endereço do emitente). Preset `stamp_and_cnpj`; o `field_id` do objeto aponta para o campo do CNPJ do tipo de documento. A transcrição vem em `text`.",
     PY_BASE.format(preset="stamp_and_cnpj"), lab("carimbo_cnpj"))
page("comprovante_pos", "Comprovante de cartão (POS) por cima",
     "Via do cliente de maquininha (Getnet/Rede/Cielo/Stone) sobreposta, com empresa, data e valor do documento. Preset `pos_overlay`/`pos_and_stamp`. Não é aplicado a documentos sem valor monetário (CC-e).",
     PY_BASE.format(preset="pos_overlay"), lab("comprovante_pos"))
page("assinatura", "Assinatura manuscrita",
     "Rubrica desenhada com curvas de Bézier. No DANFE/DACTE vai no canhoto superior; em layouts sem canhoto vai ao fim do conteúdo. Preset `signature_and_scratches`.",
     PY_BASE.format(preset="signature_and_scratches"), lab("assinatura"))

page("riscos_dobra_bordas", "Riscos de caneta, dobra e bordas de scanner",
     "Riscos de caneta, faixas de scanner, dobra de papel e bordas escuras (`apply_scratches_and_scan_borders`). Cada parte é opcional e sorteada; vem junto dos presets com artefatos.",
     """import random
from augmentation.stamps import apply_scratches_and_scan_borders

out = apply_scratches_and_scan_borders(
    image, random.Random(2026),
    add_pen_scratches=True, add_scan_borders=True, add_fold_or_streak=True,
)""",
     "Só altera pixels (não cria `special_objects` nem muda as caixas).",
     "\nCada parte isolada:\n\n| só riscos | só bordas | só dobra |\n|---|---|---|\n| ![](effects/riscos_dobra_bordas/so_riscos.jpg) | ![](effects/riscos_dobra_bordas/so_bordas.jpg) | ![](effects/riscos_dobra_bordas/so_dobra.jpg) |\n")

page("inclinacao", "Inclinação com reprojeção exata das caixas",
     "A página gira de -3,8° a +3,8° (65% das amostras) e **todas as caixas** de `elements[]` e `special_objects[]` são reprojetadas: `bbox` vira o envelope e `obb_points` guarda os 4 vértices exatos.",
     """img_aug, label, meta = augment_document(
    image, label, field_values, seed=2026,
    artifact_preset="none", scan_mode="clean_digital", angle_deg=3.0,
)""",
     f"O mesmo elemento antes e depois (mm); note o `obb_points`:\n\n```json\n{j('inclinacao/label.json')}\n```")

(EX / "modos_scanner.md").write_text("""# Modos de scanner

Efeito fotométrico final: `clean_digital` (sem alteração, 20%), `color_scan` (48%) e `bw_binarized_scan` (32%). Incluem ruído, blur, brilho/contraste e compressão JPEG (`augmentation/ops.py`).

## Como gerar

```bash
python -m pipeline.cli generate --doctype danfe --count 20 --seed 42 --out dataset   # sorteado
python examples/make_effect_examples.py                                                # este exemplo
```

```python
img_aug, label, meta = augment_document(image, label, field_values, seed=2026,
                                        artifact_preset="none", scan_mode="bw_binarized_scan", angle_deg=0.0)
```

## Antes e depois

| original | clean_digital | color_scan | bw_binarized_scan |
|---|---|---|---|
| ![](effects/modos_scanner/antes.jpg) | ![](effects/modos_scanner/clean_digital.jpg) | ![](effects/modos_scanner/color_scan.jpg) | ![](effects/modos_scanner/bw_binarized_scan.jpg) |

## O que sai

O modo escolhido fica em `metadata/<id>.meta.json` → `augmentation.scan_mode`. As caixas não mudam.
""", encoding="utf8")

page("variante_geometrica", "Variante geométrica (`images_geo/`)",
     "Distorção afim extra (Albumentations `Affine`) gravada em `images_geo/<id>.png`. **As caixas dos labels não valem para esta imagem** (`boxes_valid: false`): ela serve para treinar robustez, não para detecção.",
     "from augmentation.pipeline import augment_geometric_variant\n\nimg_geo, meta = augment_geometric_variant(image, seed=2026)",
     f"```json\n{j('variante_geometrica/meta.json')}\n```")

(EX / "oclusao_html.md").write_text(f"""# Oclusão no HTML/Markdown (`html_visible`, `md_visible`)

Carimbo, assinatura e comprovante POS são sobrepostos depois do render, então o HTML do documento (`html_clean`) não os conhece. O `html_visible` descreve **o que a imagem degradada mostra**: cada objeto vira `<aside data-kind="pos_receipt|stamp|signature|watermark">` com a transcrição, inserido depois do bloco do documento que está acima dele, e campos cobertos em ≥ 50% viram `[ilegível]`.

## Como gerar

```bash
python -m pipeline.cli generate --doctype danfe --count 20 --seed 42 --html --out dataset
```

```python
from htmlgen.occlusion import apply_degradation
from htmlgen.convert import to_clean_html, to_markdown

vis_full, relatorio = apply_degradation(html_full, label)   # label já com special_objects
html_visible = to_clean_html(vis_full)
md_visible = to_markdown(vis_full, "table")
```

## Antes e depois

| imagem limpa ↔ `html_clean` | imagem degradada ↔ `html_visible` |
|---|---|
| ![antes](effects/oclusao_html/antes.jpg) | ![depois](effects/oclusao_html/depois.jpg) |

## O que sai

Relatório (`meta.html.occlusion`):

```json
{j('oclusao_html/relatorio.json')}
```

Campos cobertos viram `[ilegível]` (em `html_visible`):

```html
{snippet_html('oclusao_html/html_visible.html', '[ilegível]', 3, 6)}
```

O comprovante, transcrito (`html_visible`):

```html
{snippet_html('oclusao_html/html_visible.html', 'data-kind="pos_receipt"', 0, 10)}
```

No `md_visible`:

```markdown
{chr(10).join(l for l in (FX / 'oclusao_html/md_visible.md').read_text('utf8').splitlines() if l.startswith('>'))[:700]}
```

Arquivos completos: [`html_clean`](effects/oclusao_html/html_clean.html), [`html_visible`](effects/oclusao_html/html_visible.html), [`md_visible`](effects/oclusao_html/md_visible.md).
""", encoding="utf8")

(EX / "README.md").write_text("""# Exemplos dos efeitos de degradação

Um exemplo de cada efeito, gerado do mesmo DANFE com seed fixa. Regenerar tudo:

```bash
python examples/make_effect_examples.py   # imagens e trechos em examples/effects/
python examples/make_effect_docs.py       # reescreve estes .md com a saída real
```

| Efeito | Página | Parâmetro principal | Onde aparece no dataset |
|---|---|---|---|
| Carimbo de recebimento | [carimbo_recebimento.md](carimbo_recebimento.md) | `artifact_preset="stamps_only"` | `images_aug/`, `labels` (`stamp`) |
| Carimbo de CNPJ | [carimbo_cnpj.md](carimbo_cnpj.md) | `"stamp_and_cnpj"` | `images_aug/`, `labels` (`stamp`) |
| Comprovante POS | [comprovante_pos.md](comprovante_pos.md) | `"pos_overlay"` | `images_aug/`, `labels` (`pos_receipt`) |
| Assinatura | [assinatura.md](assinatura.md) | `"signature_and_scratches"` | `images_aug/`, `labels` (`signature`) |
| Riscos, dobra, bordas | [riscos_dobra_bordas.md](riscos_dobra_bordas.md) | `apply_scratches_and_scan_borders` | `images_aug/` |
| Inclinação | [inclinacao.md](inclinacao.md) | `angle_deg` | `images_aug/`, `bbox`/`obb_points` |
| Modos de scanner | [modos_scanner.md](modos_scanner.md) | `scan_mode` | `images_aug/`, `meta` |
| Variante geométrica | [variante_geometrica.md](variante_geometrica.md) | `augment_geometric_variant` | `images_geo/` |
| Oclusão no HTML | [oclusao_html.md](oclusao_html.md) | `apply_degradation` | `html_visible/`, `md_visible/` |

No pipeline (`python -m pipeline.cli generate ...`) os efeitos são sorteados por amostra; `examples/dataset/` traz amostras completas e `examples/pdfs/` os PDFs de referência.
""", encoding="utf8")
