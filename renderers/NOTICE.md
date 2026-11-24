# Origem dos renderizadores

Os módulos desta pasta (`danfe/`, `dacte/`, `damdfe/`, `danfse/`, `dacce/`, `portal_nfe.py`,
`xfpdf.py`, `pdf_element.py`, `utils.py`, `generate_qrcode.py`) são derivados da biblioteca
**BrazilFiscalReport** (https://github.com/Engenere/BrazilFiscalReport), que gera os PDFs
auxiliares (DANFE, DACTE, DAMDFE, DANFSe, DACCe) a partir do XML fiscal com `fpdf2`.
Foram usados como **referência inicial** deste projeto e são mantidos aqui porque produzem
o visual real dos PDFs/imagens do dataset sintético.

- Autoria original: Engenere (Antônio S. Pereira Neto, Cristiano Mafra Junior) e
  Edson Bernardino — ver os cabeçalhos de copyright nos arquivos.
- Licença: **GNU LGPL v3** (arquivo `LICENSE` na raiz). Código derivado continua sob a mesma licença.
- Alterações neste repositório: pasta renomeada de `brazilfiscalreport/` para `renderers/`;
  remoção de documentação, CLI e testes da lib; ajustes para os presets de ERP, Portal NF-e,
  CNPJ alfanumérico e DANFSe usados pelo gerador. O restante do repositório (geradores de dados,
  augmentation, pipeline, labels, HTML) é código novo deste projeto.
