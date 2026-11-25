# Generate Synthetic Brazil Documents

Gerador de **datasets sintéticos de documentos fiscais brasileiros** para pesquisa em OCR, Document AI e modelos de visão-linguagem (VLMs). Cada amostra traz o **XML fiscal**, o **PDF**, **imagens limpas e degradadas** (scanner, carimbos, comprovantes POS, assinaturas, inclinação), **anotações** (texto com bounding boxes, KIE, objetos de layout) e, para os tipos já suportados, o **HTML e o Markdown** que descrevem a página (par imagem → HTML/MD).

> **Tudo é sintético.** Empresas, CNPJs/CPFs, chaves de acesso, QR Codes e códigos de barras não existem nem têm validade fiscal: ambiente de homologação (`tpAmb=2`) nos XMLs, chaves com UF/DV inválidos e domínios `.invalid`. Os PDFs/imagens não trazem avisos de "sem valor fiscal". Não use os arquivos como documento fiscal.

## Origem e contexto

Este projeto é **inspirado em um fork da biblioteca [BrazilFiscalReport](https://github.com/Engenere/BrazilFiscalReport)**, que gera DANFE, DACTE, DAMDFE, DANFSe e DACCe em PDF a partir do XML fiscal com `fpdf2`. A biblioteca original é mantida por Engenere (Antônio S. Pereira Neto, Cristiano Mafra Junior) e Edson Bernardino.

Ela foi a **referência inicial**: o visual dos PDFs em `renderers/` vem dela. Do fork para cá:

- saíram a CLI, a interface Streamlit, a documentação e os testes da biblioteca; ficaram os renderizadores, renomeados de `brazilfiscalreport/` para `renderers/`;
- o gerador de dados (Faker + `generator/fake_data.py`), os templates XML, os presets de ERP e a geração de CNPJ alfanumérico (IN RFB 2.229/2024) são novos;
- o pipeline produz imagem limpa e degradada, labels com bbox em mm, KIE, e HTML/Markdown pareado com cada imagem;
- tipos novos: Portal da NF-e (layouts clássico e moderno), NFS-e legada (Ginfes v03) e HTML derivado da geometria do PDF.

O objetivo é pesquisa: datasets sintéticos de documentos fiscais brasileiros para OCR, Document AI e VLMs, em que cada imagem vem com a verdade de campo do XML. A licença é a mesma da biblioteca de origem (LGPL-3.0); detalhes em [`renderers/NOTICE.md`](renderers/NOTICE.md).

## 1. Como funciona

```
seed ─► dados falsos (Faker + fake_data) ─► XML fiscal (template + preenchimento)
                                              │
              ┌───────────────────────────────┼─────────────────────────────┐
              ▼                               ▼                             ▼
   PDF real (renderers/, fpdf2)      HTML semântico + CSS          (variante geométrica)
              │                       │        │
              ▼                       ▼        ▼
   imagem limpa por página     html_clean   html (CSS) ──► Chromium ──► PDF/imagem (opcional)
              │                  + md
              ▼
   degradação (augmentation/): carimbo · assinatura · POS · inclinação · scanner
              │                                   │
              ▼                                   ▼
   images_aug + labels (OCR, bbox, OBB, KIE)   html_visible + md_visible
```

- **Determinístico e retomável:** a seed de cada amostra deriva de `(seed, tipo, split, índice)`; o `metadata/*.meta.json` é o último arquivo gravado, então rodar o mesmo comando de novo continua de onde parou. Splits 80/10/10 (`train/val/test`).
- **Renderizadores:** `renderers/` gera o **visual real** do PDF (derivado da lib BrazilFiscalReport, ver §7). O HTML segue a **mesma ordem de blocos, rótulos e larguras** desse PDF; a imagem pode vir do PDF real (`--image-source lib_pdf`, padrão) ou do próprio HTML renderizado no Chromium (`--image-source html`).
- **Diversidade:** presets de ERP (Linx, Xpert, Galago, minimal, paisagem), fontes Times/Helvetica/Courier, canhoto no topo/rodapé/lateral, tabelas de itens com moldura/grade/aberta, colunas de combustível/desconto, logos procedurais, CNPJ numérico e alfanumérico (IN RFB 2.229/2024), itens ANP/ANVISA/lote/serviço, carimbos e comprovantes POS.

## 2. Instalação e uso

```bash
pip install -e .                       # ou: uv sync
python -m playwright install chromium  # só para --html
```

```bash
# um tipo
python -m pipeline.cli generate --doctype danfe --count 1000 --workers 8 --seed 42 --out dataset
# todos os tipos
python -m pipeline.cli generate --all --count 1000 --workers 8 --out dataset
# com HTML/Markdown (todos os tipos)
python -m pipeline.cli generate --doctype danfe --count 1000 --html --out dataset
python -m pipeline.cli generate --doctype danfe --count 1000 --html --image-source html --out dataset
# auditoria e estatísticas
python -m pipeline.cli validate danfe --out dataset
python -m pipeline.cli stats danfe --out dataset
```

Opções úteis: `--cnpj-alnum-ratio 0.3` (fração de CNPJs alfanuméricos), `--workers N`, `--seed N`.

## 3. Documentos suportados

| Tipo (`--doctype`) | Documento | XML de origem | Variantes sorteadas | HTML/MD |
|---|---|---|---|---|
| `danfe` | DANFE (NF-e) | `nfeProc` | 5 ERPs (Linx, Xpert, Galago, minimal, paisagem), fonte, canhoto, tabela, colunas, logo | sim (template) |
| `nfe_portal` | Consulta do Portal da NF-e | `nfeProc` | clássico (Fazenda) e moderno (SVRS), 2 páginas | sim (do PDF) |
| `dacte` | DACTE (CT-e) | `CTe` | modal dutoviário | sim (do PDF) |
| `damdfe` | DAMDFE (MDF-e) | `MDFe` | modal aéreo | sim (do PDF) |
| `danfse` | DANFSe v2.0 (NFS-e nacional) | `NFSe` | CNPJ numérico/alfanumérico | sim (do PDF) |
| `dacce` | DACCe (carta de correção) | `procEventoNFe` | — | sim (do PDF) |
| `nfse_legado` | NFS-e legada (Ginfes v03, lote de RPS) | `EnviarLoteRpsEnvio` | 5 serviços, tomador PF/PJ, ISS 2/3/5% | sim (do PDF) |

**O HTML-alvo é só estrutura:** `section`/`header`/`h*`, `dl` com `dt`+`dd`, `table` e `p`, sem atributos, `div`, `br` nem `<head>`; logo, QR, código de barras e objetos sobrepostos viram `<img>` vazio. **Duas formas de gerar o HTML.** *DANFE:* template Jinja a partir do XML, com as mesmas caixas, larguras em mm e presets de ERP do renderizador (`htmlgen/templates/`). *Demais tipos:* o HTML é **derivado da geometria do PDF real** (`htmlgen/pdf2html.py`): as células são as regiões fechadas pelas linhas desenhadas, o texto de cada célula vira campo (`dl/dt/dd`), faixa de título (`h2`), tabela ou parágrafo, e imagens/marca d'água viram `<img>` vazio. O texto bate com a imagem por construção (`text_fidelity` ≈ 1,0); os pares rótulo/valor são heurísticos e, quando o papel de um texto é ambíguo, ele fica como `dd` sem `dt`. O mesmo DOM carrega o estilo absoluto (mm) de cada texto, então renderizado no Chromium reproduz o PDF (`--image-source html`).

Novos tipos entram pelo `pipeline/registry.py`: um adaptador em `generator/`, funções de label em `generator/labels/`, um contexto de augmentation em `augmentation/context.py` e (opcional) uma spec de HTML em `htmlgen/`.

## 4. Aplicações

- **OCR e leitura de documentos:** texto completo e por linha/span com caixas, em imagens limpas e degradadas.
- **KIE (extração de campos):** entidades chave-valor com referência à caixa (emitente, destinatário, chave, valores, datas, itens).
- **Detecção de layout e objetos:** código de barras, QR, logo, carimbo, assinatura e comprovante POS com bounding box.
- **Reconhecimento de estrutura de tabela e formulário:** o HTML limpo descreve campos (`dl`/`dt`/`dd`) e tabelas (`thead`/`tbody`) na ordem de leitura.
- **Imagem → HTML / Markdown (VLMs):** pares `images/` ↔ `html_clean/`/`md/` e, para a página degradada, `images_aug/` ↔ `html_visible/`/`md_visible/`.
- **Robustez a degradação e oclusão:** inclinação, binarização, ruído de scanner, carimbo/assinatura/POS por cima do texto; o alvo marca o coberto como `[ilegível]` e transcreve o objeto.
- **Classificação de tipo de documento** e **detecção de variante de ERP/layout** (o `metadata` guarda o preset sorteado).
- **Verificação de consistência texto ↔ imagem** (`text_fidelity`).

## 5. Anotações geradas

Por amostra (`<out>/<doctype>/…`, particionado em subpastas de 10.000):

| Pasta | Conteúdo |
|---|---|
| `xml/<id>.xml` | XML fiscal de origem (verdade de campo) |
| `pdfs/<id>.pdf` | PDF vetorial |
| `images/<id>_p<N>.png` | página N limpa (150/200/300 dpi sorteado) |
| `images_aug/<id>.png` | página 1 com artefatos físicos, inclinação e modo scanner |
| `images_geo/<id>.png` | variante com distorção geométrica (as caixas não valem aqui) |
| `labels/<id>.json` | anotações (abaixo) |
| `metadata/<id>.meta.json` | seed, dpi, páginas, preset de ERP/estilo, parâmetros de degradação, erros de campo, `text_fidelity` |
| `html_clean/`, `md/` | **com `--html`** — documento descrito sem CSS (par de `images/`) |
| `html_visible/`, `md_visible/` | **com `--html`** — o que a imagem degradada mostra (par de `images_aug/`) |
| `html/` | **com `--html`** — HTML completo com CSS (renderiza no Chromium) |
| `manifest.parquet` | índice do lote (doc_id, split, seed, `match_rate`, páginas, `text_fidelity`) |

`labels/<id>.json`:

- `pages[]`: tamanho da página em mm.
- `elements[]`: cada trecho de texto com `bbox` `{x,y,w,h}` em mm (após a rotação, com `obb_points` — os 4 vértices exatos), `text`, `field_ids`.
- `ocr`: `full_text` e texto por página.
- `kie`: entidades por papel (`issuer`, `recipient`, `document`, `totals`, `items`…), com `tax_id_type` (`cnpj_numeric`, `cnpj_alnum`, `cpf`) e referência ao elemento (`bbox_ref`).
- `layout.special_objects[]`: `barcode`, `qrcode`, `logo`, `stamp` (`receipt_stamp`, `cnpj_stamp`), `signature`, `pos_receipt`; stamp/POS trazem `text` com a **transcrição** do objeto.
- `extraction_stats`: campos conhecidos × casados com uma caixa (`match_rate`); `source`: caminhos e seed.

**Degradações no alvo HTML (`html_visible`).** Carimbos, assinaturas e comprovantes POS são sobrepostos depois do render, então só aparecem no `html_visible`: cada objeto vira um `<img>` vazio (só a sinalização; tipo e transcrição ficam em `labels/`), inserido depois do bloco do documento que está acima dele; campos cobertos em ≥ 50% (pela caixa já rotacionada) viram `[ilegível]`. Valores repetidos (ex.: `0,00`) só são marcados quando todas as ocorrências estão cobertas.

**`text_fidelity`:** fração dos tokens do HTML limpo presentes no texto do PDF que gerou a imagem (≈ 0,98 no DANFE, onde há números quebrados em coluna estreita — o que o renderizador original também faz — e 1,0 nos tipos derivados do PDF).

**PDFs de exemplo da NFS-e legada por capital** (leiautes de São Paulo, Porto Velho, Fortaleza, Maceió e Rio Branco, reconstruídos a partir de notas reais): [`examples/pdfs/`](examples/pdfs/) — `nfse_sao_paulo.pdf`, `nfse_porto_velho.pdf`, `nfse_fortaleza.pdf`, `nfse_maceio.pdf`, `nfse_rio_branco.pdf`. Os dados são sintéticos; o leiaute é o da prefeitura.

**Exemplos de cada efeito** (carimbos, POS, assinatura, riscos, inclinação, scanner, variante geométrica, oclusão no HTML), com comando e saída real: [`examples/README.md`](examples/README.md). **Um exemplo de cada tipo e variação:** [`examples/tipos.md`](examples/tipos.md). **NFS-e legada** (PDF, imagem, label, KIE e Markdown de 3 amostras): [`examples/nfse_legado.md`](examples/nfse_legado.md).

## 6. Estrutura do código

| Pasta | Função |
|---|---|
| `generator/` | dados falsos, templates XML e geradores por tipo (`generator/templates/upstream_fixtures/`: XMLs de origem para novos templates), labels e KIE |
| `renderers/` | renderizadores PDF (fpdf2) por tipo — ver §7 |
| `htmlgen/` | HTML/Markdown: modelo/template (DANFE) e `pdf2html.py` (demais tipos), `specs/`, Chromium, oclusão, fidelidade |
| `augmentation/` | carimbos, assinaturas, POS, inclinação, scanner e reprojeção de caixas; `context.py` define o contexto por tipo |
| `pipeline/`, `export/`, `validation/`, `rasterization/` | CLI, fluxo por amostra, escrita/manifesto, auditoria, PDF → imagem |

API em Python (exemplo com DANFE):

```python
from generator.danfe import generate_danfe, render_kwargs
from renderers.danfe import Danfe

xml_str, fv = generate_danfe(seed=100, cnpj_alnum_ratio=0.5, erp_preset="classic_landscape")
Danfe(xml=xml_str, **render_kwargs(fv)).output("danfe.pdf")   # presets: linx_autosystem, xpert, galago, minimal_open, classic_landscape
```

```python
from augmentation.pipeline import augment_document
from pipeline.registry import DOCTYPES

spec = DOCTYPES["danfe"]
img_aug, label, meta = augment_document(
    image, label, fv, seed=100,
    artifact_preset="pos_overlay",   # none | stamps_only | stamp_and_cnpj | pos_overlay | pos_and_stamp | signature_and_scratches
    scan_mode="bw_binarized_scan",   # clean_digital | color_scan | bw_binarized_scan
    angle_deg=-2.5,
    context=spec.augment_context(fv),
)
```

## 7. Créditos e licença

Os renderizadores PDF em `renderers/` são derivados da biblioteca **[BrazilFiscalReport](https://github.com/Engenere/BrazilFiscalReport)** (Engenere; Edson Bernardino), usada como **referência inicial** deste projeto. O restante (geradores de dados, augmentation, pipeline, labels, HTML) é código novo. Licença **LGPL-3.0** (`LICENSE`); detalhes e alterações em `renderers/NOTICE.md`.

Os bindings XSD da NFS-e legada vêm da biblioteca `nfselib-legacy` (import `nfselib`), usada só para serializar o envelope Ginfes v03 em `generator/nfse_legado.py`.

### Uso para pesquisa

Este projeto é de **pesquisa**. Os dados são **sintéticos** e o código é disponibilizado para **uso livre em pesquisa acadêmica e científica**, por qualquer pessoa, sem uso comercial. Os termos completos estão em [`LICENSE-PESQUISA.md`](LICENSE-PESQUISA.md). Os renderizadores de `renderers/` continuam sob **LGPL-3.0** (`LICENSE`), por serem derivados da biblioteca original.

## 8. Exemplos práticos

### 8.1 Gerar pelo terminal

```bash
# 200 DANFEs com HTML/Markdown, seed fixa (mesmo comando = mesmo dataset)
python -m pipeline.cli generate --doctype danfe --count 200 --seed 42 --html --out dataset

# NFS-e legada (Ginfes): 50 amostras com imagens, labels, HTML e Markdown
python -m pipeline.cli generate --doctype nfse_legado --count 50 --seed 42 --html --out dataset

# imagem degradada renderizada a partir do próprio HTML (exige Chromium: python -m playwright install chromium)
python -m pipeline.cli generate --doctype dacte --count 20 --html --image-source html --out dataset

# o lote é retomável: rodar de novo continua a partir do que já foi gravado
python -m pipeline.cli generate --doctype nfse_legado --count 50 --seed 42 --html --out dataset

# auditoria e estatísticas do lote
python -m pipeline.cli validate nfse_legado --out dataset
python -m pipeline.cli stats nfse_legado --out dataset
```

Tipos aceitos em `--doctype`: `danfe`, `nfe_portal`, `dacte`, `damdfe`, `danfse`, `dacce`, `nfse_legado`.

### 8.2 Só o PDF de um documento

Útil para testar um renderizador ou gerar PDFs avulsos, sem imagem nem anotação:

```python
from pipeline.registry import DOCTYPES

spec = DOCTYPES["nfse_legado"]
xml_str, field_values, render_kwargs = spec.generate(seed=100, cnpj_alnum_ratio=0.3)
spec.render(xml_str, render_kwargs).output("nfse_legado.pdf")
```

O mesmo vale para os outros tipos (`danfe`, `dacte`, `damdfe`, `danfse`, `dacce`, `nfe_portal`); no DANFE, `render_kwargs` traz o preset de ERP sorteado.

### 8.3 Uma amostra completa, em Python

`generate_one` faz o fluxo inteiro (XML → PDF → imagem → labels → degradação → gravação) e devolve uma linha de resumo:

```python
from pathlib import Path
from pipeline.single import generate_one

row = generate_one(
    "nfse_legado", split="train", index=0, run_seed=42,
    out_dir=Path("dataset"), html=True, force=True,
)
print(row["doc_id"], row["match_rate"], row["text_fidelity"])
# nfse_legado_train_00000000 1.0 1.0
```

Para controlar a degradação de uma página, use `augment_document` diretamente (exemplo completo na seção 6).

### 8.4 NFS-e legada, ponto a ponto

Do envelope Ginfes até o label, para entender cada etapa:

```python
from pathlib import Path

from generator.labels.layout import build_label, flatten_nfse_legado_fields
from generator.labels.kie import build_kie_nfse_legado
from pipeline.registry import DOCTYPES

spec = DOCTYPES["nfse_legado"]

# 1. dados falsos + XML Ginfes (string) + kwargs que o envelope não traz
xml_str, fv, render_kwargs = spec.generate(seed=7)
print(fv["razao_social_prestador"], fv["cnpj_prestador"], fv["v_serv"], fv["v_iss"])

# 2. PDF de uma página (leiaute de referência em fpdf2)
pdf_bytes = bytes(spec.render(xml_str, render_kwargs).output())
Path("nfse_legado.pdf").write_bytes(pdf_bytes)

# 3. textos que o PDF imprime, já formatados (CNPJ com máscara, valores 1.234,56)
print(flatten_nfse_legado_fields(fv)["valor_iss"])   # ex.: 701,63

# 4. label: cada campo casado com o bbox do PDF; o KIE usa o mesmo casamento
label = build_label("nfse_legado.pdf", fv, doc_type="NFSE_LEGADO", doc_id="demo",
                    source={}, flatten_fn=flatten_nfse_legado_fields)
label["kie"] = build_kie_nfse_legado(fv, label.pop("field_id_to_element"))
print(label["extraction_stats"])     # {'fields_total': 19, 'fields_matched_to_bbox': 19, 'match_rate': 1.0}
```

Para o formato completo de cada etapa, veja [`examples/nfse_legado.md`](examples/nfse_legado.md).

### 8.5 Ler o dataset gerado

```python
import json
from pathlib import Path

import pyarrow.parquet as pq

root = Path("dataset/nfse_legado")

# índice do lote (um registro por amostra)
for row in pq.read_table(root / "manifest.parquet").to_pylist()[:3]:
    print(row["doc_id"], row["split"], row["match_rate"])

# anotações de uma amostra
label = json.loads(next((root / "labels").rglob("*.json")).read_text(encoding="utf8"))
for e in label["elements"]:
    if e["field_ids"]:
        print(e["field_ids"], e["bbox"], e["text"])   # bbox em mm
print(label["kie"]["provider"]["cnpj"]["value"], label["kie"]["service"]["value"]["value"])

# pares para treinar imagem → HTML/Markdown: imagem degradada ↔ o que ela mostra
stem = Path(next((root / "images_aug").rglob("*.png"))).stem
html_visible = next((root / "html_visible").rglob(f"{stem}.html"))
md_visible = next((root / "md_visible").rglob(f"{stem}.md"))
```

Os pares de treino são sempre por amostra: `images/` ↔ `html_clean/` e `md/`; `images_aug/` ↔ `html_visible/` e `md_visible/` (o que a imagem degradada realmente mostra, com carimbos transcritos e campos cobertos marcados como `[ilegível]`).

### 8.6 Novo tipo de documento

Um tipo entra em quatro passos, sem mexer no pipeline: um gerador em `generator/<tipo>.py` que devolve `(xml_str, field_values)`, um renderizador em `renderers/<tipo>.py`, funções `flatten_<tipo>_fields` e `build_kie_<tipo>` em `generator/labels/`, e uma entrada em `pipeline/registry.py` (além de uma spec de HTML em `htmlgen/`, se houver). O caso da NFS-e legada, em `generator/nfse_legado.py`, `renderers/nfse_legado.py`, `generator/labels/layout.py` e `kie.py`, é um bom modelo.
