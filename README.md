# Generate Synthetic Brazil Documents

Gerador de **documentos fiscais brasileiros sintéticos** para pesquisa em OCR, Document AI e modelos de visão-linguagem. Cada amostra traz o XML fiscal, o PDF, imagens limpas e degradadas, anotações (texto com bounding box, campos e objetos) e, para os tipos suportados, o HTML e o Markdown da página.

> **Uso para pesquisa.** Os dados são sintéticos: empresas, CNPJs, CPFs, chaves de acesso e QR Codes não são reais, e os documentos não têm validade fiscal. O código é livre para pesquisa, ensino e uso não comercial. Termos em [`LICENSE-PESQUISA.md`](LICENSE-PESQUISA.md).

Os renderizadores de `renderers/` são derivados do [BrazilFiscalReport](https://github.com/Engenere/BrazilFiscalReport) (LGPL-3.0). Detalhes em [`renderers/NOTICE.md`](renderers/NOTICE.md) e [`LICENSE`](LICENSE).

## Instalação

```bash
pip install -e .
python -m playwright install chromium   # só para --image-source html
```

## Uso

```bash
# 100 amostras de um tipo, com HTML e Markdown
python -m pipeline.cli generate --doctype danfe --count 100 --seed 42 --html --out dataset

# todos os tipos
python -m pipeline.cli generate --all --count 100 --out dataset

# conferir e resumir um lote
python -m pipeline.cli validate danfe --out dataset
python -m pipeline.cli stats danfe --out dataset
```

Opções úteis: `--seed` (mesma seed, mesmo lote), `--workers N`, `--cnpj-alnum-ratio 0.3` (fração de CNPJs alfanuméricos), `--image-source html` (imagem renderizada do HTML, em vez do PDF). O lote é retomável: rodar o mesmo comando de novo continua de onde parou.

## Tipos de documento

| `--doctype` | Documento | Variações |
|---|---|---|
| `danfe` | DANFE (NF-e) | 6 leiautes de ERP |
| `nfe_portal` | Consulta do Portal da NF-e | clássico (Fazenda) e moderno (SVRS) |
| `dacte` | DACTE (CT-e) | modal dutoviário |
| `damdfe` | DAMDFE (MDF-e) | modal aéreo |
| `danfse` | DANFSe v2.0 (NFS-e nacional) | CNPJ numérico e alfanumérico |
| `dacce` | DACCe (carta de correção) | — |
| `nfse_legado` | NFS-e legada (Ginfes v03) | Ginfes, 5 capitais e 5 genéricos |

Veja todos os leiautes e efeitos visualmente na **[galeria](examples/galeria.md)**.

## Saída

Cada amostra gera, em `<out>/<doctype>/`:

| Pasta | Conteúdo |
|---|---|
| `xml/` | XML fiscal de origem (verdade de campo) |
| `pdfs/` | PDF vetorial |
| `images/` | página limpa (150, 200 ou 300 dpi) |
| `images_aug/` | página com degradações: carimbo, assinatura, POS, inclinação, scanner |
| `labels/` | anotações em JSON (abaixo) |
| `html_clean/`, `md/` | com `--html`: documento descrito sem CSS, par de `images/` |
| `html_visible/`, `md_visible/` | com `--html`: o que a imagem degradada mostra, par de `images_aug/` |
| `manifest.parquet` | índice do lote |

O `labels/<id>.json` traz `elements` (cada trecho de texto com `bbox` em mm e os 4 vértices exatos), `ocr` (texto completo e por página), `kie` (campos por papel: emitente, destinatário, totais, itens) e `layout.special_objects` (carimbos, QR, código de barras, assinatura, POS, com a transcrição).

Os splits são 80/10/10 (`train/val/test`). A seed de cada amostra deriva de `(seed, tipo, split, índice)`, então o mesmo comando gera o mesmo lote.

## Exemplos

- [`examples/galeria.md`](examples/galeria.md): uma imagem de cada tipo, variação e efeito.
- [`examples/pdfs/`](examples/pdfs/): PDFs de exemplo, incluindo a NFS-e legada por capital.
- [`examples/README.md`](examples/README.md): antes e depois de cada efeito de degradação, com o parâmetro que o liga.
- [`examples/nfse_legado.md`](examples/nfse_legado.md): uma amostra completa da NFS-e legada, do XML ao Markdown.

## Código

| Pasta | Função |
|---|---|
| `generator/` | dados falsos, XML, geradores por tipo e labels |
| `renderers/` | PDFs (fpdf2) de cada tipo |
| `htmlgen/` | HTML e Markdown de cada tipo |
| `augmentation/` | degradações: carimbo, assinatura, POS, inclinação, scanner |
| `pipeline/` | CLI e fluxo por amostra |
| `export/`, `validation/`, `rasterization/` | escrita do lote, auditoria, PDF para imagem |

Para gerar um PDF ou uma amostra direto em Python, veja `pipeline/single.py` (`generate_one`) e `pipeline/registry.py` (`DOCTYPES`).

Para adicionar um tipo: um gerador em `generator/<tipo>.py`, um renderizador em `renderers/<tipo>.py`, as funções de label em `generator/labels/` e uma entrada em `pipeline/registry.py`. A NFS-e legada é o modelo.

## Testes

```bash
pytest -q
```
