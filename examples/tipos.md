# Um exemplo de cada tipo de documento e suas variações

Gerado por `python examples/make_type_examples.py` (pipeline unificado, `--html`, seed 2026).
Cada pasta em [`types/`](types/) tem a estrutura de saída completa: `images/` (limpa) ↔ `html_clean/`, `md/`; `images_aug/` (degradada) ↔ `html_visible/`, `md_visible/`; `html/`, `xml/`, `labels/`, `metadata/`.

| Tipo | Variação | O que muda | Págs. | Fidelidade | Imagem | HTML-alvo |
|---|---|---|---|---|---|---|
| `danfe` | `linx_autosystem` | ERP Linx: colunas de combustível (ANP), tabela com grade vertical, crédito no rodapé | 1 | 0.9898 | [limpa](types/danfe__linx_autosystem/danfe/images/0000/danfe_train_00000000_p1.jpg) · [degradada](types/danfe__linx_autosystem/danfe/images_aug/0000/danfe_train_00000000.jpg) | [html_clean](types/danfe__linx_autosystem/danfe/html_clean/0000/danfe_train_00000000.html) · [md](types/danfe__linx_autosystem/danfe/md/0000/danfe_train_00000000.md) · [html_visible](types/danfe__linx_autosystem/danfe/html_visible/0000/danfe_train_00000000.html) |
| `danfe` | `xpert` | ERP Xpert: coluna VALOR LÍQ., crédito no emitente e no rodapé | 1 | 0.9883 | [limpa](types/danfe__xpert/danfe/images/0000/danfe_train_00000000_p1.jpg) · [degradada](types/danfe__xpert/danfe/images_aug/0000/danfe_train_00000000.jpg) | [html_clean](types/danfe__xpert/danfe/html_clean/0000/danfe_train_00000000.html) · [md](types/danfe__xpert/danfe/md/0000/danfe_train_00000000.md) · [html_visible](types/danfe__xpert/danfe/html_visible/0000/danfe_train_00000000.html) |
| `danfe` | `galago` | ERP Galago: ISSQN, logo e crédito no meio da página | 1 | 0.9914 | [limpa](types/danfe__galago/danfe/images/0000/danfe_train_00000000_p1.jpg) · [degradada](types/danfe__galago/danfe/images_aug/0000/danfe_train_00000000.jpg) | [html_clean](types/danfe__galago/danfe/html_clean/0000/danfe_train_00000000.html) · [md](types/danfe__galago/danfe/md/0000/danfe_train_00000000.md) · [html_visible](types/danfe__galago/danfe/html_visible/0000/danfe_train_00000000.html) |
| `danfe` | `minimal_open` | Tabela de itens aberta embaixo, sem moldura inferior | 1 | 0.9915 | [limpa](types/danfe__minimal_open/danfe/images/0000/danfe_train_00000000_p1.jpg) · [degradada](types/danfe__minimal_open/danfe/images_aug/0000/danfe_train_00000000.jpg) | [html_clean](types/danfe__minimal_open/danfe/html_clean/0000/danfe_train_00000000.html) · [md](types/danfe__minimal_open/danfe/md/0000/danfe_train_00000000.md) · [html_visible](types/danfe__minimal_open/danfe/html_visible/0000/danfe_train_00000000.html) |
| `danfe` | `classic_landscape` | DANFE em paisagem com canhoto lateral | 1 | 0.9739 | [limpa](types/danfe__classic_landscape/danfe/images/0000/danfe_train_00000000_p1.jpg) · [degradada](types/danfe__classic_landscape/danfe/images_aug/0000/danfe_train_00000000.jpg) | [html_clean](types/danfe__classic_landscape/danfe/html_clean/0000/danfe_train_00000000.html) · [md](types/danfe__classic_landscape/danfe/md/0000/danfe_train_00000000.md) · [html_visible](types/danfe__classic_landscape/danfe/html_visible/0000/danfe_train_00000000.html) |
| `danfe` | `padrao` | Layout padrão (sem ERP específico) | 1 | 0.9913 | [limpa](types/danfe__padrao/danfe/images/0000/danfe_train_00000000_p1.jpg) · [degradada](types/danfe__padrao/danfe/images_aug/0000/danfe_train_00000000.jpg) | [html_clean](types/danfe__padrao/danfe/html_clean/0000/danfe_train_00000000.html) · [md](types/danfe__padrao/danfe/md/0000/danfe_train_00000000.md) · [html_visible](types/danfe__padrao/danfe/html_visible/0000/danfe_train_00000000.html) |
| `nfe_portal` | `classic_fazenda` | Consulta clássica do Portal Nacional (cartões bege) | 2 | 1.0 | [limpa](types/nfe_portal__classic_fazenda/nfe_portal/images/0000/nfe_portal_train_00000002_p1.jpg) · [degradada](types/nfe_portal__classic_fazenda/nfe_portal/images_aug/0000/nfe_portal_train_00000002.jpg) | [html_clean](types/nfe_portal__classic_fazenda/nfe_portal/html_clean/0000/nfe_portal_train_00000002.html) · [md](types/nfe_portal__classic_fazenda/nfe_portal/md/0000/nfe_portal_train_00000002.md) · [html_visible](types/nfe_portal__classic_fazenda/nfe_portal/html_visible/0000/nfe_portal_train_00000002.html) |
| `nfe_portal` | `modern_svrs` | Consulta moderna do Portal SVRS (cartões brancos) | 2 | 1.0 | [limpa](types/nfe_portal__modern_svrs/nfe_portal/images/0000/nfe_portal_train_00000002_p1.jpg) · [degradada](types/nfe_portal__modern_svrs/nfe_portal/images_aug/0000/nfe_portal_train_00000002.jpg) | [html_clean](types/nfe_portal__modern_svrs/nfe_portal/html_clean/0000/nfe_portal_train_00000002.html) · [md](types/nfe_portal__modern_svrs/nfe_portal/md/0000/nfe_portal_train_00000002.md) · [html_visible](types/nfe_portal__modern_svrs/nfe_portal/html_visible/0000/nfe_portal_train_00000002.html) |
| `dacte` | `dutoviario` | CT-e do modal dutoviário (único modal gerado hoje) | 1 | 1.0 | [limpa](types/dacte__dutoviario/dacte/images/0000/dacte_train_00000000_p1.jpg) · [degradada](types/dacte__dutoviario/dacte/images_aug/0000/dacte_train_00000000.jpg) | [html_clean](types/dacte__dutoviario/dacte/html_clean/0000/dacte_train_00000000.html) · [md](types/dacte__dutoviario/dacte/md/0000/dacte_train_00000000.md) · [html_visible](types/dacte__dutoviario/dacte/html_visible/0000/dacte_train_00000000.html) |
| `damdfe` | `aereo` | MDF-e do modal aéreo (único modal gerado hoje) | 1 | 1.0 | [limpa](types/damdfe__aereo/damdfe/images/0000/damdfe_train_00000000_p1.jpg) · [degradada](types/damdfe__aereo/damdfe/images_aug/0000/damdfe_train_00000000.jpg) | [html_clean](types/damdfe__aereo/damdfe/html_clean/0000/damdfe_train_00000000.html) · [md](types/damdfe__aereo/damdfe/md/0000/damdfe_train_00000000.md) · [html_visible](types/damdfe__aereo/damdfe/html_visible/0000/damdfe_train_00000000.html) |
| `danfse` | `padrao` | DANFSe v2.0 (NFS-e nacional) | 1 | 1.0 | [limpa](types/danfse__padrao/danfse/images/0000/danfse_train_00000000_p1.jpg) · [degradada](types/danfse__padrao/danfse/images_aug/0000/danfse_train_00000000.jpg) | [html_clean](types/danfse__padrao/danfse/html_clean/0000/danfse_train_00000000.html) · [md](types/danfse__padrao/danfse/md/0000/danfse_train_00000000.md) · [html_visible](types/danfse__padrao/danfse/html_visible/0000/danfse_train_00000000.html) |
| `dacce` | `padrao` | Carta de correção eletrônica | 1 | 1.0 | [limpa](types/dacce__padrao/dacce/images/0000/dacce_train_00000000_p1.jpg) · [degradada](types/dacce__padrao/dacce/images_aug/0000/dacce_train_00000000.jpg) | [html_clean](types/dacce__padrao/dacce/html_clean/0000/dacce_train_00000000.html) · [md](types/dacce__padrao/dacce/md/0000/dacce_train_00000000.md) · [html_visible](types/dacce__padrao/dacce/html_visible/0000/dacce_train_00000000.html) |
| `nfse_legado` | `ginfes` | NFS-e legada, leiaute de referência Ginfes v03 (lote de RPS) | 1 | 1.0 | [limpa](types/nfse_legado__ginfes/nfse_legado/images/0000/nfse_legado_train_00000000_p1.jpg) · [degradada](types/nfse_legado__ginfes/nfse_legado/images_aug/0000/nfse_legado_train_00000000.jpg) | [html_clean](types/nfse_legado__ginfes/nfse_legado/html_clean/0000/nfse_legado_train_00000000.html) · [md](types/nfse_legado__ginfes/nfse_legado/md/0000/nfse_legado_train_00000000.md) · [html_visible](types/nfse_legado__ginfes/nfse_legado/html_visible/0000/nfse_legado_train_00000000.html) |
| `nfse_legado` | `sao_paulo` | São Paulo: brasão, caixa número/data/código, Intermediário, retenções e Outras Informações | 1 | 1.0 | [limpa](types/nfse_legado__sao_paulo/nfse_legado/images/0000/nfse_legado_train_00000000_p1.jpg) · [degradada](types/nfse_legado__sao_paulo/nfse_legado/images_aug/0000/nfse_legado_train_00000000.jpg) | [html_clean](types/nfse_legado__sao_paulo/nfse_legado/html_clean/0000/nfse_legado_train_00000000.html) · [md](types/nfse_legado__sao_paulo/nfse_legado/md/0000/nfse_legado_train_00000000.md) · [html_visible](types/nfse_legado__sao_paulo/nfse_legado/html_visible/0000/nfse_legado_train_00000000.html) |
| `nfse_legado` | `porto_velho` | Porto Velho (molde de notas reais): Prestador/Tomador, código do serviço, retenções federais | 1 | 1.0 | [limpa](types/nfse_legado__porto_velho/nfse_legado/images/0000/nfse_legado_train_00000000_p1.jpg) · [degradada](types/nfse_legado__porto_velho/nfse_legado/images_aug/0000/nfse_legado_train_00000000.jpg) | [html_clean](types/nfse_legado__porto_velho/nfse_legado/html_clean/0000/nfse_legado_train_00000000.html) · [md](types/nfse_legado__porto_velho/nfse_legado/md/0000/nfse_legado_train_00000000.md) · [html_visible](types/nfse_legado__porto_velho/nfse_legado/html_visible/0000/nfse_legado_train_00000000.html) |
| `nfse_legado` | `fortaleza` | Fortaleza: grade de identificação, detalhamento de valores e cálculo do ISSQN | 1 | 1.0 | [limpa](types/nfse_legado__fortaleza/nfse_legado/images/0000/nfse_legado_train_00000000_p1.jpg) · [degradada](types/nfse_legado__fortaleza/nfse_legado/images_aug/0000/nfse_legado_train_00000000.jpg) | [html_clean](types/nfse_legado__fortaleza/nfse_legado/html_clean/0000/nfse_legado_train_00000000.html) · [md](types/nfse_legado__fortaleza/nfse_legado/md/0000/nfse_legado_train_00000000.md) · [html_visible](types/nfse_legado__fortaleza/nfse_legado/html_visible/0000/nfse_legado_train_00000000.html) |
| `nfse_legado` | `maceio` | Maceió: Secretaria de Economia, prestador/tomador e quadro de valores | 1 | 1.0 | [limpa](types/nfse_legado__maceio/nfse_legado/images/0000/nfse_legado_train_00000000_p1.jpg) · [degradada](types/nfse_legado__maceio/nfse_legado/images_aug/0000/nfse_legado_train_00000000.jpg) | [html_clean](types/nfse_legado__maceio/nfse_legado/html_clean/0000/nfse_legado_train_00000000.html) · [md](types/nfse_legado__maceio/nfse_legado/md/0000/nfse_legado_train_00000000.md) · [html_visible](types/nfse_legado__maceio/nfse_legado/html_visible/0000/nfse_legado_train_00000000.html) |
| `nfse_legado` | `rio_branco` | Rio Branco: Secretaria de Finanças e campos rótulo: valor | 1 | 1.0 | [limpa](types/nfse_legado__rio_branco/nfse_legado/images/0000/nfse_legado_train_00000000_p1.jpg) · [degradada](types/nfse_legado__rio_branco/nfse_legado/images_aug/0000/nfse_legado_train_00000000.jpg) | [html_clean](types/nfse_legado__rio_branco/nfse_legado/html_clean/0000/nfse_legado_train_00000000.html) · [md](types/nfse_legado__rio_branco/nfse_legado/md/0000/nfse_legado_train_00000000.md) · [html_visible](types/nfse_legado__rio_branco/nfse_legado/html_visible/0000/nfse_legado_train_00000000.html) |
| `nfse_legado` | `generico_faixa` | Estilo genérico (inventado, não é de uma cidade) | 1 | 1.0 | [limpa](types/nfse_legado__generico_faixa/nfse_legado/images/0000/nfse_legado_train_00000000_p1.jpg) · [degradada](types/nfse_legado__generico_faixa/nfse_legado/images_aug/0000/nfse_legado_train_00000000.jpg) | [html_clean](types/nfse_legado__generico_faixa/nfse_legado/html_clean/0000/nfse_legado_train_00000000.html) · [md](types/nfse_legado__generico_faixa/nfse_legado/md/0000/nfse_legado_train_00000000.md) · [html_visible](types/nfse_legado__generico_faixa/nfse_legado/html_visible/0000/nfse_legado_train_00000000.html) |
| `nfse_legado` | `generico_tabela` | Estilo genérico (inventado, não é de uma cidade) | 1 | 1.0 | [limpa](types/nfse_legado__generico_tabela/nfse_legado/images/0000/nfse_legado_train_00000000_p1.jpg) · [degradada](types/nfse_legado__generico_tabela/nfse_legado/images_aug/0000/nfse_legado_train_00000000.jpg) | [html_clean](types/nfse_legado__generico_tabela/nfse_legado/html_clean/0000/nfse_legado_train_00000000.html) · [md](types/nfse_legado__generico_tabela/nfse_legado/md/0000/nfse_legado_train_00000000.md) · [html_visible](types/nfse_legado__generico_tabela/nfse_legado/html_visible/0000/nfse_legado_train_00000000.html) |
| `nfse_legado` | `generico_grade` | Estilo genérico (inventado, não é de uma cidade) | 1 | 1.0 | [limpa](types/nfse_legado__generico_grade/nfse_legado/images/0000/nfse_legado_train_00000000_p1.jpg) · [degradada](types/nfse_legado__generico_grade/nfse_legado/images_aug/0000/nfse_legado_train_00000000.jpg) | [html_clean](types/nfse_legado__generico_grade/nfse_legado/html_clean/0000/nfse_legado_train_00000000.html) · [md](types/nfse_legado__generico_grade/nfse_legado/md/0000/nfse_legado_train_00000000.md) · [html_visible](types/nfse_legado__generico_grade/nfse_legado/html_visible/0000/nfse_legado_train_00000000.html) |
| `nfse_legado` | `generico_pontilhado` | Estilo genérico (inventado, não é de uma cidade) | 1 | 1.0 | [limpa](types/nfse_legado__generico_pontilhado/nfse_legado/images/0000/nfse_legado_train_00000000_p1.jpg) · [degradada](types/nfse_legado__generico_pontilhado/nfse_legado/images_aug/0000/nfse_legado_train_00000000.jpg) | [html_clean](types/nfse_legado__generico_pontilhado/nfse_legado/html_clean/0000/nfse_legado_train_00000000.html) · [md](types/nfse_legado__generico_pontilhado/nfse_legado/md/0000/nfse_legado_train_00000000.md) · [html_visible](types/nfse_legado__generico_pontilhado/nfse_legado/html_visible/0000/nfse_legado_train_00000000.html) |
| `nfse_legado` | `generico_colunas` | Estilo genérico (inventado, não é de uma cidade) | 1 | 1.0 | [limpa](types/nfse_legado__generico_colunas/nfse_legado/images/0000/nfse_legado_train_00000000_p1.jpg) · [degradada](types/nfse_legado__generico_colunas/nfse_legado/images_aug/0000/nfse_legado_train_00000000.jpg) | [html_clean](types/nfse_legado__generico_colunas/nfse_legado/html_clean/0000/nfse_legado_train_00000000.html) · [md](types/nfse_legado__generico_colunas/nfse_legado/md/0000/nfse_legado_train_00000000.md) · [html_visible](types/nfse_legado__generico_colunas/nfse_legado/html_visible/0000/nfse_legado_train_00000000.html) |

## Prévia (imagens degradadas)

**danfe / linx_autosystem**  
![danfe linx_autosystem](types/danfe__linx_autosystem/danfe/images_aug/0000/danfe_train_00000000.jpg)

**danfe / xpert**  
![danfe xpert](types/danfe__xpert/danfe/images_aug/0000/danfe_train_00000000.jpg)

**danfe / galago**  
![danfe galago](types/danfe__galago/danfe/images_aug/0000/danfe_train_00000000.jpg)

**danfe / minimal_open**  
![danfe minimal_open](types/danfe__minimal_open/danfe/images_aug/0000/danfe_train_00000000.jpg)

**danfe / classic_landscape**  
![danfe classic_landscape](types/danfe__classic_landscape/danfe/images_aug/0000/danfe_train_00000000.jpg)

**danfe / padrao**  
![danfe padrao](types/danfe__padrao/danfe/images_aug/0000/danfe_train_00000000.jpg)

**nfe_portal / classic_fazenda**  
![nfe_portal classic_fazenda](types/nfe_portal__classic_fazenda/nfe_portal/images_aug/0000/nfe_portal_train_00000002.jpg)

**nfe_portal / modern_svrs**  
![nfe_portal modern_svrs](types/nfe_portal__modern_svrs/nfe_portal/images_aug/0000/nfe_portal_train_00000002.jpg)

**dacte / dutoviario**  
![dacte dutoviario](types/dacte__dutoviario/dacte/images_aug/0000/dacte_train_00000000.jpg)

**damdfe / aereo**  
![damdfe aereo](types/damdfe__aereo/damdfe/images_aug/0000/damdfe_train_00000000.jpg)

**danfse / padrao**  
![danfse padrao](types/danfse__padrao/danfse/images_aug/0000/danfse_train_00000000.jpg)

**dacce / padrao**  
![dacce padrao](types/dacce__padrao/dacce/images_aug/0000/dacce_train_00000000.jpg)

**nfse_legado / ginfes**  
![nfse_legado ginfes](types/nfse_legado__ginfes/nfse_legado/images_aug/0000/nfse_legado_train_00000000.jpg)

**nfse_legado / sao_paulo**  
![nfse_legado sao_paulo](types/nfse_legado__sao_paulo/nfse_legado/images_aug/0000/nfse_legado_train_00000000.jpg)

**nfse_legado / porto_velho**  
![nfse_legado porto_velho](types/nfse_legado__porto_velho/nfse_legado/images_aug/0000/nfse_legado_train_00000000.jpg)

**nfse_legado / fortaleza**  
![nfse_legado fortaleza](types/nfse_legado__fortaleza/nfse_legado/images_aug/0000/nfse_legado_train_00000000.jpg)

**nfse_legado / maceio**  
![nfse_legado maceio](types/nfse_legado__maceio/nfse_legado/images_aug/0000/nfse_legado_train_00000000.jpg)

**nfse_legado / rio_branco**  
![nfse_legado rio_branco](types/nfse_legado__rio_branco/nfse_legado/images_aug/0000/nfse_legado_train_00000000.jpg)

**nfse_legado / generico_faixa**  
![nfse_legado generico_faixa](types/nfse_legado__generico_faixa/nfse_legado/images_aug/0000/nfse_legado_train_00000000.jpg)

**nfse_legado / generico_tabela**  
![nfse_legado generico_tabela](types/nfse_legado__generico_tabela/nfse_legado/images_aug/0000/nfse_legado_train_00000000.jpg)

**nfse_legado / generico_grade**  
![nfse_legado generico_grade](types/nfse_legado__generico_grade/nfse_legado/images_aug/0000/nfse_legado_train_00000000.jpg)

**nfse_legado / generico_pontilhado**  
![nfse_legado generico_pontilhado](types/nfse_legado__generico_pontilhado/nfse_legado/images_aug/0000/nfse_legado_train_00000000.jpg)

**nfse_legado / generico_colunas**  
![nfse_legado generico_colunas](types/nfse_legado__generico_colunas/nfse_legado/images_aug/0000/nfse_legado_train_00000000.jpg)
