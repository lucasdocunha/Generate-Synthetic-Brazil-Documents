# Oclusão no HTML/Markdown (`html_visible`, `md_visible`)

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
{
  "artifacts": [
    "pos_receipt",
    "signature"
  ],
  "occluded_nodes": 11
}
```

Campos cobertos viram `[ilegível]` (em `html_visible`):

```html
              <td>CX</td>
              <td>8,00</td>
              <td>141,70</td>
              <td>[ilegível]</td>
              <td>[ilegível]</td>
              <td>[ilegível]</td>
              <td>0,00</td>
              <td>[ilegível]</td>
              <td>0,00</td>
```

O comprovante, transcrito (`html_visible`):

```html
      <aside data-kind="pos_receipt">
        <p>cielo</p>
        <p>REDE CIELO - Via Cliente</p>
        <p>SERVIÇOS DE MACHADO MEI</p>
        <p>PRAIA NICOLE PASTOR 646</p>
        <p>MATINA - BA</p>
        <p>TK.SCX.EIV/5THQ-33 CV:39968745</p>
        <p>25/07/2023 17:39:35 AUT:541046</p>
        <p>DOC:921426 TERM:0700381</p>
        <p>MASTERCARD            ************9975</p>
```

No `md_visible`:

```markdown
> **Assinatura**
> [assinatura manuscrita]
> **Comprovante de cartão (POS)**
> cielo
> REDE CIELO - Via Cliente
> SERVIÇOS DE MACHADO MEI
> PRAIA NICOLE PASTOR 646
> MATINA - BA
> TK.SCX.EIV/5THQ-33 CV:39968745
> 25/07/2023 17:39:35 AUT:541046
> DOC:921426 TERM:0700381
> MASTERCARD ************9975
> CVAD:983322
> DEBITO A VISTA
> VALOR: 182.903,64
```

Arquivos completos: [`html_clean`](effects/oclusao_html/html_clean.html), [`html_visible`](effects/oclusao_html/html_visible.html), [`md_visible`](effects/oclusao_html/md_visible.md).
