# Exemplos dos efeitos de degradação

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

NFS-e legada (Ginfes v03, lote de RPS, sem efeito de degradação próprio): [`nfse_legado.md`](nfse_legado.md), gerado por `python examples/make_nfse_examples.py`.
