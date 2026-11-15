# tpl_002 — proveniência

Estrutura montada a partir das fixtures do próprio repositório (testes do
renderer, origem OCA/brazil-fiscal-report), com todos os valores trocados por
placeholders — nenhum dado de documento real permanece:

- `tests/fixtures/danfe/nfe_retirada_entrega.xml` — blocos `retirada`/`entrega`
- `tests/fixtures/danfe/nfe_big_font_size.xml` — `transp` (transporta/vol) e `cobr`
- `tests/fixtures/danfe/nfe_overload.xml` — `ISSQNtot`
- `tests/fixtures/danfe/nfe_reforma_tributaria.xml` — `IBSCBSTot` (simplificado, sem gMono)
- `tests/fixtures/danfe/nfe_with_production_environment.xml` — envelope `nfeProc`/`protNFe` (montado por código)

O `<dest>` contém CNPJ e CPF ao mesmo tempo apenas como esqueleto; o gerador
remove um dos dois.
