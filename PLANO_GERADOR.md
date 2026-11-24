# Plano — Gerador de Dataset Sintético de Documentos Fiscais Brasileiros

> **Nota (atualização):** a pasta `brazilfiscalreport/` citada neste plano foi renomeada para `renderers/` e passou a ser mantida neste projeto (testes e fixtures da lib removidos; ver `renderers/NOTICE.md`). A decisão original de manter os renderizadores "intocados" vale como histórico.


## Contexto

Este documento responde ao pedido em `gerador.md`: um plano completo (arquitetura, pastas, fluxo, stack, bibliotecas, templates, formato de labels, e estratégias de geração/anti-validade/OCR/layout/KIE/VQA/expansão/dificuldades) para transformar o fork `brazilfiscalreport` — já limpo na Fase 1 anterior (docs/CLI/Streamlit removidos, só o pacote renderizador + testes permanecem) — em um framework de geração de dataset sintético de 10.000+ documentos por tipo (DANFE, DACTE, DAMDFE, DANFSE, DACCe), com ground truth completo para OCR, Layout Analysis, KIE e VQA. **Nada foi implementado ainda** — este é só o plano para validação, conforme pedido explicitamente no `gerador.md`.

**Decisão confirmada nesta rodada**: os renderizadores em `brazilfiscalreport/` permanecem **100% intocados**. Onde os três agentes de design convergiram em sugerir pequenos patches aditivos (metadado de PDF, embutir fontes TTF, watermark do DANFSE/DACCe, domínio do QR do DANFSE), o plano abaixo adota alternativas que não tocam o renderizador, ou assume a lacuna como limitação conhecida do v1 (documentado explicitamente em cada caso, nunca escondido).

---

## 1. Arquitetura completa do projeto

Sete componentes independentes, cada um um pacote Python importável/testável isoladamente (entrada/saída em dict/dataclass ou arquivo), conforme pedido ("geração de dados, renderização, geração dos labels, augmentations, exportação, validação, configuração"):

```
configuração ──▶ geração de dados ──▶ renderização (brazilfiscalreport/, intocado)
                                            │
                                            ▼
                                   geração de labels (captura de campos + derivação OCR/layout/KIE/VQA)
                                            │
                                            ▼
                                     augmentations
                                            │
                                            ▼
                                      exportação ──▶ validação
                                            │
                                            ▼
                                     orquestração (CLI + batch runner, une tudo)
```

- **Renderização**: os 5 renderizadores existentes, usados como biblioteca, sem modificação. A única extensão necessária (captura de bounding boxes) já foi escopada em rodada anterior como um flag opcional `record_fields=True` em `xFPDF` — **essa extensão também é uma alteração ao renderizador**; como a decisão desta rodada foi "renderizadores 100% intocados", ela precisa ser revalidada com o usuário antes da implementação (ver "Questões em aberto").
- **Geração de dados + geração de labels**: pacote novo `generator/` (detalhado em §2, §6).
- **Augmentations, Exportação, Validação, Orquestração**: quatro pacotes novos (`augmentation/`, `export/`, `validation/`, `pipeline/`).

Princípio central: "não quero código específico para cada documento" **não pode** se aplicar à renderização (os 5 renderizadores encodam leiautes reais da SEFAZ, são necessariamente código por tipo) — mas **deve e pode** se aplicar a geração, labeling, augmentation, exportação e validação, que devem ser um motor genérico único, dirigido por configuração declarativa por tipo de documento (§6).

---

## 2. Organização das pastas

### Código

```
brazilfiscalreport/            # existente, intocado
generator/
  fake_data.py                  # CNPJ/CPF (validate-docbr), chave de acesso, endereços/IBGE, telefone, datas, nomes (Faker pt_BR)
  code_tables.py                # NCM/CFOP/CST — tabelas oficiais completas (§5.1)
  xml_builder.py                 # motor genérico de substituição/repetição de template
  schemas/{danfe,dacte,damdfe,danfse,dacce}.yaml   # config declarativa por tipo (§6.3)
  templates/{danfe,dacte,...}/v1/tpl_NNN/{source.xml, manifest.yaml, PROVENANCE.md}
  data/{ncm_full.json, cfop_full.json, cst_*.json, municipios_ibge.csv}
  branding/logo_factory.py        # logos fictícios procedurais (Pillow)
  fonts/                          # não aplicável neste v1 (ver §9/§15 — sem patch no renderer, sem TTF novo)
  kie_schema/{danfe,dacte,...}.yaml   # mapa declarativo field_values → esquema KIE (§13)
  danfe.py dacte.py damdfe.py danfse.py dacce.py   # adaptadores finos por tipo (§6.4)
  labels/{ocr.py, layout.py, kie.py, vqa.py}        # derivação de ground truth
rasterization/raster.py          # PDF → imagem(ns)
augmentation/{pipeline.py, ops.py}
export/{writer.py, sharding.py, manifest.py}
validation/{schemas.py, auditor.py}
pipeline/{config.py, single.py, batch.py, cli.py}
config/default.yaml               # config de execução (contagem, seed, workers, splits)
tests/                            # existente, + testes novos por pacote acima
```

### Dataset de saída

```
dataset/
  danfe/
    train|val|test/
      images/0000/danfe_train_00001234.png
      pdfs/0000/danfe_train_00001234.pdf
      xml/0000/danfe_train_00001234.xml
      labels/0000/danfe_train_00001234.json      # arquivo canônico único (§7)
      metadata/0000/danfe_train_00001234.meta.json
    manifest.parquet
  dacte/ damdfe/ danfse/ dacce/    (mesma subárvore)
  dataset_manifest.parquet
exports/                            # gerado sob demanda, nunca autoritativo (§7)
  danfe/{coco/, kie/, vqa/, ocr/}
```

Convenção de nome: `<tipo>_<split>_<id de 8 dígitos>.<ext>`, sharding em subpastas de 4 dígitos a cada 10.000 ids (evita diretórios com dezenas de milhares de arquivos). Split (train/val/test) atribuído na geração, não por shuffle posterior — para DANFE (19 templates), recomenda-se split *por template* (val/test só veem layouts não vistos em train); para tipos com poucos templates (DACCe: 1), split por template é inviável — usar amostragem aleatória simples com essa limitação documentada.

---

## 3. Fluxo de geração

### Por documento
```
1. seed = hash(run_seed, doctype, split, sample_index)     # determinístico, independente de ordem/worker
2. schema = load(generator/schemas/<tipo>.yaml)
3. template = escolher_template(tipo, rng)                  # generator/templates/<tipo>/...
4. field_values, xml_str = build_xml(template, schema, rng)  # fake_data.py + code_tables.py + regras anti-validade (§9)
5. validar(field_values)                                     # pydantic, fail-fast
6. pdf_obj = ADAPTER[tipo](xml_str, config=render_config, record_fields=True)
7. field_records = pdf_obj.get_recorded_fields(); pdf_bytes = pdf_obj.output()
8. pdf_bytes = stamp_metadata(pdf_bytes)                      # metadado "SYNTHETIC" via pós-processamento (§9)
9. images = rasterize(pdf_bytes, dpi=escolha_variável)        # PyMuPDF
10. images_aug, aug_params = augment(images, rng, split)
11. labels = derive_labels(field_records, schema, tipo)       # OCR/layout/KIE/VQA (§7,10-13)
12. validar(labels)                                            # segundo gate pydantic
13. export.write_sample(...)                                    # grava tudo no dataset/
14. manifest.append(...)
```

### Em lote (10.000+ por tipo, 50.000+ total)
- **Paralelismo**: `joblib.Parallel(n_jobs=workers, backend="loky")`, um work-unit = uma amostra completa e independente.
- **Reprodutibilidade**: seed derivado por hash estável de `(run_seed, doctype, split, sample_index)` — nunca `run_seed + index` puro (evitar correlação entre índices vizinhos).
- **Checkpoint/retomada**: presença de um `meta.json` válido (escrito por último, atomicamente, só após exportação completa) = "amostra pronta". Resumir = rodar o mesmo comando de novo; nenhum job-queue externo necessário.
- **Falhas**: amostra que falha validação/renderização é tentada 1x com seed derivado diferente; se falhar de novo, registrada em `.failed_samples.jsonl` e pulada — uma combinação ruim não trava um lote de 10.000.
- **Progresso**: `tqdm`/log por tipo/split, taxa de amostras/seg, contagem de falhas — logado em `dataset/<tipo>/.runlogs/`.

---

## 4. Tecnologias recomendadas

| Necessidade | Escolha | Justificativa |
|---|---|---|
| Rasterização PDF→imagem | **PyMuPDF** (`pymupdf`) | Instalável via pip (sem binário externo como Poppler), renderiza in-process (mais rápido em lote), controla DPI/zoom diretamente — atende "diferentes resoluções" |
| Augmentation | **Albumentations** como motor, com conjunto de operações curado especificamente para documentos (não presets de foto) | Rotação leve (±0,5–3°), ruído gaussiano, blur leve, brilho/contraste, artefatos JPEG, downscale-upscale — excluir hue/flip/cutout (sem análogo em documento real) |
| Validação de dados | **pydantic** (já instalado) | Dois gates: `FieldValues` (pré-render) e `LabelRecord`/`ManifestRow` (pré-export) |
| CLI | **Typer** (já instalado) | `python -m pipeline.cli generate --doctype danfe --count 10000 --workers 8 --seed 42` |
| Paralelismo | **joblib** (já instalado) | Pool de processos com reuso de worker, progresso e captura de exceção prontos |
| Manifesto/índice | **plain files + Parquet sidecar** (`pyarrow`) | Na escala de 50.000 documentos (~15-40GB estimado), WebDataset/LMDB resolvem problemas que este dataset ainda não tem, e custam a conveniência de abrir um arquivo à mão durante o desenvolvimento |
| Metadado de PDF sem tocar o renderer | **pypdf** (ou PyMuPDF) para pós-processar os bytes do PDF já gerado | Ver §9 — evita alterar `xfpdf.py` |

---

## 5. Bibliotecas recomendadas

### 5.1 NCM/CFOP/CST — tabelas oficiais completas
Não existe pacote PyPI mantido que já embale essas tabelas. Fonte primária: Receita Federal/Siscomex publica a tabela NCM completa e vigente como JSON público sem autenticação (`portalunico.siscomex.gov.br/classif/api/publico/nomenclatura/download/json`, ~12.000 códigos); CFOP (SPED/Receita, ~600 códigos) e CST (poucas dezenas por família) são tabelas pequenas e estáveis. **Recomendação**: um script único (`generator/data/refresh_ncm.py`), não parte do caminho quente de geração, baixa/converte essas fontes para JSON estático versionado em `generator/data/`; `code_tables.py` carrega esses arquivos estáticos (offline, determinístico), nunca a rede em tempo de geração.

### 5.2 Identificadores e dados fake
`validate-docbr` (CNPJ/CPF/IE), `Faker('pt_BR')` (nomes/empresas), `phonenumbers` (telefones válidos por formato), `brazilfiscalreport/danfse/municipios_ibge.csv` (município/UF/CEP consistentes, reaproveitado).

### 5.3 Logos fictícios: geração procedural via Pillow, não biblioteca curada
Uma biblioteca de imagens fixas (dezenas/centenas) se repetiria a cada N documentos — o mesmo problema de "documento repetido" que o usuário quer evitar. Recomenda-se um "logo synthesizer": forma de fundo (círculo/quadrado/hexágono, sorteada) + paleta de 2 cores "brand-safe" + monograma de 1-3 letras **derivado do nome da empresa daquele mesmo documento** (coerência logo↔nome), renderizado em memória com Pillow, sem biblioteca externa nova além da já usada para imagens (`BytesIO`, como já feito em `dacce.py`/`danfe_code.py`).

### 5.4 Lista consolidada de dependências novas
`pymupdf`, `albumentations` (+ `opencv-python-headless`), `tqdm`, `pyarrow`, `validate-docbr`, `pypdf`. Já instalados e reaproveitados: `Faker`, `phonenumbers`, `pydantic`/`pydantic-settings`, `typer`/`click`, `joblib`, `Pillow`, `python-barcode`, `qrcode`.

---

## 6. Estrutura dos templates

Um "template" = **(um XML de fixture real como esqueleto) + (um manifesto descrevendo o que é substituível/repetível/mutuamente consistente)**:

```
generator/templates/danfe/v1/tpl_001/
  source.xml        # idêntico/derivado de generator/templates/upstream_fixtures/danfe/*.xml
  manifest.yaml       # overrides específicos deste template (faixa de repetição de <det>, blocos opcionais presentes)
  PROVENANCE.md        # de qual fixture original veio, quando importado
```

`tests/fixtures/` (removido; os XMLs foram para `generator/templates/upstream_fixtures/`) era a suíte de regressão dos renderizadores — não é reaproveitada em runtime, é **copiada** para `generator/templates/` na criação inicial (podendo divergir depois, ex. para marcar regiões repetíveis), para nunca arriscar as baselines de teste existentes.

### O mecanismo que de fato entrega "sem código por tipo de documento"

`generator/schemas/<tipo>.yaml` — consumido por um único motor genérico (`xml_builder.py`) — declara, por tipo:
```yaml
doctype: danfe
namespace: "http://www.portalfiscal.inf.br/nfe"
fields:
  - {name: emit_cnpj, xpath: ./NFe/infNFe/emit/CNPJ, generator: fake_data.cnpj, consistency_group: emitente}
  - {name: chave_acesso, xpath: "@Id", generator: fake_data.access_key, consistency_group: identificacao}
repeatable:
  - name: det
    xpath: ./NFe/infNFe/det
    count_range: [1, 40]
    subfields: [{name: prod_descricao, xpath: ./prod/xProd, generator: fake_data.product_description}, ...]
consistency_groups:
  emitente: [emit_cnpj, emit_xNome, ...]
  identificacao: [chave_acesso, data_emissao, ...]
variants:
  icms_st: {tax_configuration: ICMS_ST}
```
Adicionar um 6º tipo de documento **nunca exige** nova lógica de substituição/repetição/consistência — isso vive uma única vez em `xml_builder.py`. O que é necessário por tipo novo (ver §14): pelo menos 1 template, este YAML, um adaptador fino (§6.4), e — só se o tipo for genuinely novo — uma nova classe de renderer.

### Adaptador (§6.4)
Como os 5 renderizadores não compartilham a mesma assinatura de construtor (DACCe recebe `emitente`/`image` fora de banda, não parseia emitente do XML), um adaptador fino por tipo (`generator/danfe.py`, `generator/dacce.py`, ...) normaliza tudo para uma interface única (`render(xml_str, render_config, record_fields=True) -> xFPDF`), sem modificar os renderizadores em si.

---

## 7. Formato dos labels

**Decisão**: um único arquivo JSON canônico por documento (`labels/<id>.json`) — não múltiplos arquivos por tarefa. Exportadores finos (`export_ocr`, `export_layout_coco`, `export_kie`, `export_vqa`) derivam formatos específicos (COCO para layout, JSONL para VQA, etc.) sob demanda, sempre a partir do mesmo arquivo canônico — nunca duplicando a geração de fatos, só reformatando.

Esquema (resumido — todo `element_id` é a chave de junção entre `elements[]` e as visões `layout`/`ocr`/`kie`/`vqa`):
```jsonc
{
  "doc_id": "danfe_00001234", "doc_type": "DANFE", "schema_version": "1.0",
  "source": {"xml_path": "...", "pdf_path": "...", "fixture_template": "nfe_test_1.xml", "generation_seed": 123},
  "pages": [{"page_number": 1, "orientation": "P", "size_mm": {"w": 210.0, "h": 297.0}}],
  "elements": [
    {"element_id": "e00042", "field_id": "emit_cnpj_cpf", "role": "content", "block_id": "b_emitente",
     "page": 1, "bbox": {"x":12.0,"y":34.5,"w":40.0,"h":4.0,"unit":"mm"},
     "text": "12.345.678/0001-99", "raw_value": "12345678000199", "draw_call": "multi_cell"}
  ],
  "layout": {"lines": [...], "blocks": [{"block_id":"b_emitente","bbox":{...},"element_ids":[...]}],
             "tables": [{"table_id":"t_products","rows":[{"row_index":1,"cell_element_ids":[...]}]}],
             "special_objects": [{"type":"qrcode","bbox":{...}}, {"type":"logo","bbox":{...}}]},
  "ocr": {"full_text": "...", "pages": [{"page_number":1, "text":"...", "line_element_ids":[...]}]},
  "kie": {"issuer": {"cnpj": {"value":"...", "raw_value":"...", "bbox_ref":"e00042"}}, "totals": {...}, "items": [...]},
  "vqa": [{"qa_id":"...", "template_id":"extractive.issuer_cnpj", "question":"...", "answer":"...",
           "question_type":"extractive", "difficulty":"easy", "supporting_field_ids":["e00042"]}]
}
```
Coordenadas em `mm` no arquivo canônico — conversão para pixel só acontece no export/rasterização, a um DPI escolhido, aplicada consistentemente à imagem e às boxes.

---

## 8. Estratégia para geração dos dados sintéticos

- **Nomes/empresas**: compor `{prefixo setorial} {termo Faker} {sufixo societário}` (LTDA/ME/EIRELI/S.A./MEI, com pesos realistas) em vez de `faker.company()` cru — evita padrão repetitivo perceptível em milhares de amostras.
- **Descrição de produto**: gerador combinatório `{categoria} {material/variante} {atributo opcional}` carregado de listas por segmento (não `faker.sentence()`), com NCM sorteado **consistente com a categoria** (tabela categoria→prefixo NCM), para que o modelo de KIE aprenda associação produto↔NCM real, não ruído.
- **Diversidade estrutural, não só numérica**: sortear um "perfil de complexidade" por documento (minimal/standard/full) que ativa/desativa blocos que os próprios renderizadores já tratam como opcionais (confirmado no código): retirada/entrega e fatura/duplicatas no DANFE (`danfe.py:977-981,1096-1099`), modal de transporte no DACTE (`dacte.py:2489-2497`), contingência no DAMDFE (`damdfe.py:259-279`), IBS/CBS (reforma tributária, fixture `nfe_reforma_tributaria.xml` já existe como referência). Quantidade de itens de linha de uma distribuição log-normal truncada (1-60), não uniforme — reflete a cauda longa real e é o gatilho natural de paginação.
- **Campos livres** (`infCpl`, observações, motivo de correção): templates com placeholders sorteados de um banco de frases modulares, não uma frase Faker genérica — importante porque esses campos viram ground truth de KIE/VQA e precisam de variação lexical real.

---

## 9. Estratégia para evitar qualquer validade fiscal

### 9.1 CPF/CNPJ/chave de acesso — válido-mas-inexistente vs. inválido

| Abordagem | Vantagens | Desvantagens |
|---|---|---|
| **Válido (checksum correto), presumivelmente inexistente** | Ensina o formato correto de dígito verificador; nenhum validador externo "reclama" | Risco de colisão real e não-trivial — CPF tem ~200M+ emitidos dentro de um subespaço válido de 1 bilhão (~20% de densidade); CNPJ tem dezenas de milhões dentro de um subespaço de 1 trilhão (~4 ordens de magnitude mais seguro, mas não zero em 50.000+ documentos) |
| **Deliberadamente inválido** | Garantia **matemática e auditável** de zero colisão (nenhum CPF/CNPJ real tem checksum quebrado) — a interseção com documentos reais é vazia por construção, não por sorte estatística | Um validador de checksum a jusante rejeitaria o campo (irrelevante para OCR/KIE, que leem texto, não recomputam módulo 11) |

**Recomendação adotada**: **CPF sempre com checksum inválido, sem exceção** (dado o risco de colisão com pessoa real e a sensibilidade de dado pessoal, não há caso de uso que justifique "válido" como padrão). **CNPJ, IE e chave de acesso: inválido por padrão, mas com um toggle de configuração** (`checksum_mode: always_invalid | always_valid`) para permitir testar validadores a jusante quando explicitamente necessário — `always_invalid` documentado como o modo do dataset de treino.

**Mecanismo**: gerar o número totalmente válido (`validate-docbr`) e corromper apenas o(s) dígito(s) verificador(es) por deslocamento fixo não-zero mod 10 (ex. `dv_final = (dv + 3) % 10`). Resultado: parece estruturalmente correto, mas falha determinística e auditavelmente em qualquer validação oficial — impossibilidade formal de colisão.

### 9.2 Chave de acesso de 44 dígitos
Camadas independentes (defesa em profundidade): (1) dígito verificador corrompido como acima; (2) o CNPJ embutido na chave é o **mesmo** CNPJ (já corrompido) do emitente daquele documento — nunca um CNPJ à parte, o que também mantém KIE coerente (CNPJ do cabeçalho = CNPJ dentro da chave); (3) `cUF` deliberadamente fora da tabela real do IBGE (ex. `"00"`/`"99"`) — verificado que nenhum renderer decodifica o `cUF` da chave para exibir UF (a UF vem de um elemento XML separado), então isso é seguro e não quebra nada.

### 9.3 Chave da NFS-e (DANFSE)
Formato definido pela especificação nacional do ADN, diferente do padrão de 44 dígitos — **não foi possível confirmar no código se há dígito verificador mod-11** (o renderer só exibe o texto cru, não valida). **Item em aberto**: checar a especificação técnica do ADN antes de implementar; na ausência de checksum próprio, a garantia recai sobre o CNPJ do emitente (usado para montar a chave) já ter DV corrompido.

### 9.4 QR Code (DACTE, DAMDFE, DANFSE) e código de barras (DANFE, DACCe)
- **DACTE/DAMDFE**: o conteúdo do QR é lido verbatim de uma tag do XML (`qrCodCTe`/`qrCodMDFe`) — o gerador tem controle total. Popular com uma URL apontando para um domínio reservado pela IANA para nunca resolver (TLD `.invalid`, RFC 2606), com comprimento de payload semelhante ao real (~100-180 caracteres) para que a densidade visual do QR gerado (sempre estruturalmente genuína, já que a lib `qrcode` gera uma matriz real para qualquer payload) fique visualmente parecida com a de um QR real.
- **DANFSE**: o domínio do QR está **hardcoded no renderer** (`https://www.nfse.gov.br/ConsultaPublica/...`) — como a decisão desta rodada foi não tocar o renderer, **isso fica como está**. Reenquadrando: isso não é necessariamente um problema — a chave embutida é derivada de um CNPJ com checksum inválido/inexistente, então, se alguém de fato escanear o QR, o portal real da NFS-e vai corretamente responder "chave não encontrada", o que é um sinal honesto de não-validade, não uma falha. Documentado como comportamento aceito, não como lacuna a esconder.
- **DANFE/DACCe (código de barras)**: ambos codificam diretamente a chave de acesso — a segurança é inteiramente herdada de §9.2, nenhum tratamento adicional necessário.

### 9.5 Watermark/rotulagem "não fiscal" — por tipo, sem tocar o renderer
- **DANFE, DACTE, DAMDFE**: já disparam automaticamente um watermark diagonal "SEM VALOR FISCAL"/"AMBIENTE DE HOMOLOGACAO" quando `tpAmb` ≠ `"1"` (`danfe.py:526,536-540,843`; `dacte.py:169,179-183`; `damdfe.py:239,247`), com defesa em profundidade (dispara também se o protocolo de autorização estiver ausente). **Regra do gerador**: sempre fixar `tpAmb=2` e nunca incluir um protocolo de autorização plausível-real — zero código novo necessário, o mecanismo já existe.
- **DANFSE**: já existe um mecanismo parcial (não descoberto na rodada anterior) — quando o ambiente é `"2"`, um texto vermelho "NFS-e SEM VALIDADE JURÍDICA" é desenhado no cabeçalho (`danfse.py:918-923`). Não é a marca d'água diagonal grande dos outros três, mas é real e já existe sem patch. **Regra do gerador**: sempre fixar ambiente=2 para DANFSE também — suficiente sem tocar o renderer.
- **DACCe**: **não há nenhum mecanismo de watermark** (confirmado, zero ocorrências no código) e, como decidido, não será adicionado nesta rodada. O disclaimer padrão já presente ("não possui validade fiscal") também aparece em CC-e reais, então não ajuda a distinguir. **Limitação aceita do v1**: a proteção do DACCe recai inteiramente sobre a garantia de identificador inválido (§9.1-9.2) — nenhum sinal visual adicional de "sintético" nesse tipo de documento. Documentado explicitamente, não escondido.

### 9.6 Metadado de PDF "sintético" — via pós-processamento, sem tocar `xfpdf.py`
Como decidido, `xfpdf.py` não é alterado. Alternativa equivalente: depois que `pdf_obj.output()` produz os bytes do PDF, um passo no `export/writer.py` reabre esses bytes com `pypdf` (ou PyMuPDF) e escreve `/Subject` = `"SYNTHETIC DOCUMENT — NOT A REAL FISCAL DOCUMENT — Generated for ML research"` e `/Keywords` = `"synthetic, not-fiscal-valid, ML-research-dataset"` antes de gravar o arquivo final — mesmo resultado (metadado descobrível por auditoria/`exiftool`, invisível ao olho humano), sem qualquer alteração ao pacote `brazilfiscalreport/`.

### 9.7 Nome do emitente — não marcar visivelmente
Não usar um padrão tipo "FICTÍCIA"/"SINTÉTICO" no `xNome` visível — prejudicaria o treino de OCR/KIE (o modelo aprenderia um atalho lexical espúrio que documentos reais nunca têm). O marcador "isto é sintético" deve viver só no `meta.json`/label canônico (`"synthetic": true`) e no metadado de PDF (§9.6), nunca no texto renderizado.

---

## 10. Estratégia para VQA

Cada par pergunta/resposta é **gerado, nunca autorado**, como função `(kie_tree, doc_type) -> VQAPair` sobre a mesma árvore `kie` do arquivo canônico — correção por construção, nunca uma string solta que possa divergir do KIE.

### Taxonomia e banco de templates (39 templates cobrindo 7 categorias)
- **(a) Extrativas/diretas** (fácil): CNPJ do emitente, nome do destinatário, data de emissão, número/série, chave de acesso, valor total, endereço, CFOP, descrição de item — 16 templates, a maioria universal, alguns por tipo (modal de transporte no DACTE, placa do veículo no DAMDFE, motivo da correção no DACCe).
- **(b) Contagem**: quantos itens/volumes/documentos vinculados existem — 3 templates.
- **(c) Comparativa/raciocínio**: produto de maior quantidade, item de maior valor, frete vs. desconto — 5 templates.
- **(d) Agregação/aritmética**: soma de ICMS de todos os itens, valor médio por item, diferença total-vs-produtos — 4 templates. Requer que valores numéricos no KIE sejam tipados (não strings formatadas) para evitar parsing frágil de "R$ 1.950,00".
- **(e) Booleana/existência**: existe desconto, ambiente de homologação, mais de uma página, regime Simples Nacional — 6 templates.
- **(f) Negativa/distratora** (crítica contra alucinação): "qual o valor do desconto?" quando não há desconto → resposta "não há desconto informado" em vez de pular o template — deliberadamente **preferir** gerar essas perguntas justamente quando o valor é ausente/zero, já que é o caso que mais ensina o modelo a não alucinar. 3 templates, cada um com uma string de resposta "não consta" autorada uma vez por campo (o único ponto do design de VQA que não é 100% mecânico, mas é um custo fixo pequeno, não por documento).
- **(g) Referência cruzada entre documentos**: fora de escopo — exigiria uma camada de vinculação de entidades entre documentos que não está desenhada aqui; reformulado como pergunta extrativa dentro do mesmo documento onde possível (ex. "qual a chave da NF-e vinculada a este CT-e" em vez de comparar com outro documento do dataset).

Cada par carrega `template_id`, `question_type`, `difficulty` (heurística: fácil=lookup único; médio=contagem/booleana/comparação simples; difícil=agregação multi-item e todas as negativas/distratoras — heurística inicial, a validar empiricamente), e `supporting_field_ids` (ligação de volta aos bboxes, para VQA "grounded").

**Aberto**: quantos pares gerar por documento (todos os templates aplicáveis vs. amostra estratificada por tipo/dificuldade no nível do dataset, para não desbalancear a favor do tipo com mais templates aplicáveis).

---

## 11. Estratégia para Layout Analysis

Mapeamento do que o usuário pediu (palavra, linha, bloco, tabela, célula, QR, código de barras, logotipo) para o mecanismo de captura:

| Elemento | Fonte | Capturado direto? |
|---|---|---|
| Linha | `xFPDF.cell`/`multi_cell`, um bbox por linha física via os próprios quad-points internos do fpdf2 | Sim |
| Palavra | Derivado — dividir o texto da linha e remedir largura de cada palavra com `get_string_width` na mesma fonte usada no draw | Não nativo, mas viável (ver §12) |
| Bloco | União das bboxes dos elementos-membro; para DANFE, `DanfeBlock` já agrupa campos — só precisa de um `block_id`; para os outros 4 renderizadores, um `with self.block("nome"):` (mesmo padrão de custo do `field()` já escopado) | Parcial — precisa de tagging incremental |
| Tabela/célula | Para a tabela de produtos do DANFE, cai de graça da captura de `multi_cell` (fpdf2 usa `Table` → `multi_cell` internamente); para grades dos outros 4 renderizadores (sem objeto `Table`), precisa de tagging com índice linha/coluna — trabalho manual real, não gratuito | Parcial |
| QR Code / código de barras / logotipo | Todos desenhados via `self.image(...)` — capturados como `role`/`type` específico se o ponto de chamada for tagueado | Sim, se tagueado |

**Formato de exportação recomendado**: COCO (categorias `word/line/block/table/cell/qrcode/barcode/logo`) — forte encaixe específico para layout (diferente de OCR/KIE, que não são detection-style), gerado só na etapa de exportação (conversão mm→px no DPI escolhido ali, nunca no arquivo canônico).

---

## 12. Estratégia para OCR

Texto corrido em ordem de leitura, montado uma única vez no momento de gerar o label (não recalculado por cada exportador), a partir do stream não-ordenado de `elements[]`:

1. Descartar `role == "decoration"`; QR/código de barras vão para `layout.special_objects`, não para o texto.
2. Agrupar elementos na mesma "linha de leitura" por proximidade de `y` (tolerância proporcional à altura da fonte, já que chamadas independentes de `cell()` no mesmo "renglão" visual podem ter `y` ligeiramente diferentes).
3. Dentro de uma linha, ordenar por `x`; entre linhas, ordenar por `y`.
4. **Caso especial da tabela de produtos**: não aplicar a regra genérica y-então-x — ler linha por linha, esquerda para direita, usando os limites de coluna já conhecidos da tabela (DANFE: `table._compute_rows_info()`, já chamado em `danfe.py:1450`); para os 4 renderizadores sem objeto `Table`, cair na regra genérica e marcar `"table_reading_order": "approximate"` no metadado até que o tagging de grade exista.
5. Concatenar linhas com `\n`, páginas com marcador de quebra; manter `ocr.pages[].line_element_ids` como fonte autoritativa e `full_text` como conveniência derivada.

**Palavra vs. linha**: a captura nativa é por linha/célula. Bboxes de palavra são deriváveis (remedir largura com a mesma fonte) mas com acúmulo de pequeno erro em alinhamentos centralizados/justificados — recomendado como **melhoria incremental depois do pipeline em nível de linha estar validado**, não bloqueante para a v1.

---

## 13. Estratégia para KIE

Esquema **aninhado** (`issuer`/`recipient`/`document`/`totals`/`items[]`), espelhando a própria estrutura do XML (`<emit>`, `<dest>`, `<det>`) — evita a explosão de chaves `item_1_descricao`, `item_2_descricao` de um esquema plano, já que a contagem de itens varia por documento.

Cada folha é um objeto `{"value", "raw_value"/"numeric_value", "bbox_ref"}` — nunca um escalar solto — para que consumidores que querem KIE ligado a bbox (treino de tagger estilo LayoutLM) e consumidores que só querem valor limpo (avaliação de LLM) leiam a mesma estrutura.

**Derivação**: um "mapa de esquema KIE" declarativo por tipo (`generator/kie_schema/<tipo>.yaml`), listando qual chave do `field_values` (gerado na montagem do XML) alimenta qual caminho KIE, e a qual `field_id` ligar o `bbox_ref`. Um construtor de KIE único e genérico percorre esse mapa — **zero código por tipo de documento**, só um arquivo de configuração novo por tipo. `bbox_ref: null` é esperado e normal (nem todo valor tem uma chamada de desenho própria — ex. um número de rua embutido numa linha de endereço combinada) — não deve ser tratado como bug.

---

## 14. Estratégia para expansão futura

Checklist para adicionar um tipo de documento hipotético novo:
1. Confirmar se um renderizador existente serve ou se é preciso um novo `brazilfiscalreport/<novo>/` (único passo genuinamente manual e por tipo — leiautes da SEFAZ são de fato bespoke).
2. Instrumentar a captura de campos no novo renderizador (mecânico, seguindo o padrão já estabelecido).
3. Adicionar ao menos 1 template (`generator/templates/<novo>/v1/tpl_001/`).
4. Escrever `generator/schemas/<novo>.yaml` (campos, repetíveis, grupos de consistência, variantes).
5. Escrever o adaptador fino `generator/<novo>.py` (poucas linhas).
6. Escrever `generator/kie_schema/<novo>.yaml`.
7. Estender `validation/schemas.py` com um modelo pydantic para o novo tipo.
8. Registrar o tipo em `pipeline/config.py` (um dict/enum) — CLI e batch driver passam a reconhecer `--doctype <novo>` automaticamente.
9. Confirmar a estratégia anti-validade-fiscal do novo tipo (§9) — expressável como `generator:`/`variant:` na config declarativa, nunca código novo de pipeline.
10. Gerar um lote pequeno (~50), rodar `validation/auditor.py`, inspecionar visualmente, então escalar.

Nenhum desses passos toca `augmentation/`, `rasterization/`, `export/` ou o driver de lote — genuinamente agnósticos de tipo de documento uma vez que adaptador/esquema/template existam.

---

## 15. Possíveis dificuldades técnicas e soluções

- **Esgotamento do pool de templates**: com 1 (DACCe) a 19 (DANFE) fixtures alimentando 10.000 amostras/tipo, a diversidade de valores/campo tem teto real quando o esqueleto estrutural é sempre o mesmo (DACCe tem só 1 esqueleto). *Solução em camadas*: esgotar primeiro diversidade de campo/repetição (quase grátis); ponderar a seleção de template para não deixar um dominar; **priorizar como ação concreta antes de escalar**: buscar/criar mais fixtures de DACCe/DAMDFE/DANFSE (hoje 1/9/6) — mais barato que qualquer engenharia de mutação estrutural. Mutação estrutural além do pool de fixtures fica fora do escopo inicial.
- **Performance**: custo estimado por amostra (XML + render fpdf2 + rasterização PyMuPDF + augmentation + labels) na casa de 50-200ms single-thread → 50.000 amostras em 40-170 min com 1 core, confortavelmente sob 1h com paralelismo de 8-16 processos.
- **Espaço em disco**: estimativa de 1-4 MB/amostra (dominado pela imagem rasterizada) → **50-200 GB para 50.000 documentos**. PNG para a imagem "limpa"/canônica (fidelidade de ground truth); JPEG reservado para a variante deliberadamente degradada de augmentation (reaproveita o próprio augmentation de compressão em vez de uma decisão de formato à parte).
- **Determinismo sob paralelismo**: resolvido por construção — seed derivado por hash de `(run_seed, doctype, split, index)`, nunca de ordem de execução/worker.
- **Coordenadas sob augmentation geométrico**: rotação/warp invalida bboxes a menos que sejam re-projetadas. *Recomendação*: manter as boxes de layout/OCR/KIE ligadas à imagem **não-augmentada geometricamente** (canônica), aplicar augmentations não-geométricos (ruído/blur/brilho/compressão/downscale) livremente sobre a imagem que carrega label, e tratar variantes com rotação/warp como um "irmão" de robustez adicional, com boxes explicitamente marcadas como não-garantidas nesse caso — evita todo o trabalho (e risco de bug) de re-projeção geométrica de coordenadas, ao custo de não ter boxes 100% exatas nas variantes rotacionadas.
- **Paginação ausente em DANFSE/DACCe** (limitação aceita, não resolvida nesta rodada por decisão de não tocar o renderer): confirmado que ambos chamam `add_page()` exatamente uma vez, sem qualquer lógica de overflow — um DANFSE com muitos serviços ou um DACCe com texto de correção muito longo simplesmente estoura/sobrepõe em vez de paginar. Se o dataset precisar desses casos, é trabalho de desenvolvimento novo no renderer, fora do escopo combinado.
- **Fonte única no DACCe / só 2-3 fontes core nos demais**: sem tocar o renderer, a diversidade tipográfica fica limitada às fontes core já disponíveis por tipo (Courier/Times, +Helvetica no DANFSE; só Helvetica fixo no DACCe) — aceito como limitação de v1, compensado por variação de margens/tamanho de fonte dentro do que a config já permite, e por variação de DPI/augmentation na imagem final.

---

## Questões em aberto (não resolvidas nesta rodada, sinalizadas explicitamente)

1. **A extensão de captura de campos (`record_fields` em `xFPDF`) também é uma alteração ao renderizador** — precisa da mesma confirmação que a decisão desta rodada resolveu para os outros patches (fontes/watermark/QR/metadado). Sem essa extensão, não há como capturar bounding boxes/labels em nenhum dos 5 tipos — é o único ponto onde "renderizador 100% intocado" entra em tensão direta com "preciso de ground truth de layout"; vale revisitar antes de iniciar a implementação de §7/§11/§12.
2. Formato da chave da NFS-e (DANFSE) — confirmar na especificação do ADN nacional se há dígito verificador, antes de implementar a corrupção de checksum (§9.3).
3. Política do projeto sobre manter ou remover por completo o modo "checksum válido" (mesmo como opção não-padrão) para CNPJ/chave de acesso (§9.1) — decisão de governança, não técnica.
4. Granularidade de OCR em nível de palavra: investir agora ou só depois de validar o pipeline em nível de linha (§12).
5. Tagging de tabela/célula com índice linha/coluna nos 4 renderizadores sem `Table` (DACTE/DAMDFE/DANFSE/DACCe) é trabalho manual real, não gratuito — precisa ser agendado explicitamente, priorizado por tipo.
6. Volume de pares VQA por documento e política de balanceamento por dificuldade/tipo no nível do dataset (§10).
7. Onde exportadores (COCO/VQA/OCR sob demanda) devem morar fisicamente na árvore do dataset, e se rodam automaticamente a cada geração ou como passo separado (§7).
8. Split treino/val/teste por template vs. aleatório puro para tipos com poucos templates (DACCe, DAMDFE, DANFSE) (§2).

## Próximos passos sugeridos (após validação deste plano)
Uma prova de conceito de fatia fina — implementar `fake_data.py` + `xml_builder.py` + gerar 1 DANFE ponta-a-ponta (XML → PDF → 1 arquivo de label canônico, mesmo que sem bbox real ainda, dado o item 1 das questões em aberto) — validaria o desenho inteiro antes de escalar para os 5 tipos e 10.000+ amostras cada.
