# Exemplos do dataset (pipeline unificado)

Gerado com `python -m pipeline.cli generate --doctype <tipo> --count N --seed 2026 --html`
(subconjunto: 3 DANFEs, 2 DACTE/DAMDFE/DANFSe/Portal NF-e e 1 DACCe, todos com HTML/Markdown). A pasta `nfse_legado/` (3 amostras, Ginfes v03) vem de `examples/make_nfse_examples.py`.
`preview.png` mostra as imagens degradadas (`images_aug/`).

Para caber no repositório, as imagens foram **reduzidas para 1240 px de largura** (≈150 dpi) e
`images_geo/` foi omitido; o `dpi` registrado em `metadata/`/`labels/` é o da geração original.
As caixas em `labels/` estão em **mm**, portanto continuam válidas em qualquer resolução.

| Pasta | Par com |
|---|---|
| `images/` (limpa) | `html_clean/`, `md/` |
| `images_aug/` (carimbo/POS/assinatura/inclinação/scanner) | `html_visible/`, `md_visible/` (artefatos em `<aside>`, campos cobertos = `[ilegível]`) |

Também: `html/` (com CSS; renderiza no Chromium), `xml/`, `pdfs/`, `labels/` (OCR, bbox/OBB, KIE, `special_objects` com transcrição), `metadata/`.
