# Projeto: Gerador de Dataset Sintético para Documentos Fiscais Brasileiros

## Objetivo

Quero desenvolver um framework capaz de gerar um grande dataset sintético de documentos fiscais brasileiros para treinamento e avaliação de modelos de IA.

O foco do projeto NÃO é gerar documentos com validade fiscal. O objetivo é produzir documentos visualmente realistas, porém completamente sintéticos, destinados exclusivamente à pesquisa em OCR, Document AI, LLMs e VLMs.

Antes de qualquer implementação, elabore um plano completo do projeto.

---

# Documentos

Os documentos atualmente suportados serão:

- DANFE
- DACTE
- DAMDFE
- DACCE
- DANFSE

O sistema deve ser projetado para permitir a inclusão de novos tipos futuramente.

---

# Objetivo do dataset

Desejo gerar pelo menos:

- 10.000 documentos de cada tipo

O dataset precisa possuir alta diversidade.

Não quero simplesmente gerar milhares de documentos iguais mudando apenas alguns números.

Cada documento deve variar em diversos aspectos.

Exemplos:

- quantidade de itens
- descrição dos produtos
- empresas
- clientes
- endereços
- datas
- horários
- impostos
- valores
- descontos
- observações
- transportadoras
- formas de pagamento
- número de páginas
- logos
- QR Codes fictícios
- códigos de barras sintéticos
- fontes
- pequenas variações de layout
- pequenas diferenças de espaçamento
- assinaturas fictícias
- carimbos
- etc.

Quanto maior a diversidade, melhor.

---

# Requisito principal

Todos os documentos devem ser completamente sintéticos.

Nunca utilizar:

- empresas reais
- CNPJs reais
- CPFs reais
- inscrições estaduais reais
- chaves de acesso reais
- QR Codes válidos
- códigos de barras válidos
- endereços reais
- telefones reais
- e-mails reais

Caso algum identificador possua algoritmo de validação (por exemplo CNPJ ou chave de acesso), analise cuidadosamente se vale a pena:

- gerar identificadores válidos matematicamente porém inexistentes;
- ou gerar identificadores completamente inválidos.

Explique as vantagens e desvantagens de cada abordagem.

Também faça uma análise de todos os elementos que conferem validade fiscal a um documento e proponha estratégias para garantir que os documentos nunca possam ser confundidos com documentos fiscais reais.

---

# Realismo

Apesar de serem sintéticos, os documentos devem ser visualmente muito próximos dos documentos reais.

O objetivo é treinar modelos que generalizem para documentos reais.

Pense em como aumentar o realismo.

Por exemplo:

- logos fictícios
- diferentes famílias tipográficas
- diferentes resoluções
- diferentes margens
- diferentes tamanhos de tabelas
- diferentes comprimentos de textos
- documentos de uma ou mais páginas

---

# Ground Truth

Cada documento deverá gerar automaticamente todas as anotações necessárias.

Pense em uma estrutura de diretórios adequada.

Exemplo:

dataset/

    danfe/

        images/

        labels/

        metadata/

Cada documento deve possuir:

- imagem
- PDF
- JSON estruturado
- XML utilizado para geração

---

# Informações que devem existir no Ground Truth

Além do documento, precisamos produzir informações para diversos tipos de modelos.

## OCR

Texto completo.

---

## Layout Analysis

Bounding boxes de todos os elementos.

Exemplo:

- palavra
- linha
- bloco
- tabela
- célula
- QR Code
- código de barras
- logotipo

---

## Key Information Extraction

Campos estruturados.

Exemplo:

- emitente
- destinatário
- CNPJ
- endereço
- número
- série
- data
- valor total
- impostos
- produtos
- quantidades
- preços

---

## Classificação

Cada documento deve possuir sua classe.

Exemplo:

- DANFE
- DACTE
- DAMDFE
- DACCE
- DANFSE

---

## VQA (Visual Question Answering)

O sistema também deve gerar automaticamente perguntas e respostas sobre cada documento.

Exemplos:

- Qual é o CNPJ do emitente?
- Qual o valor total?
- Quantos produtos existem?
- Qual o maior valor de item?
- Qual a data de emissão?
- Qual o nome da empresa?
- Qual é o destinatário?
- Qual produto possui maior quantidade?
- Existe desconto?
- Qual o imposto destacado?
- Qual é a chave do documento?
- Qual é o número da nota?
- Qual a série?

Gostaria que você propusesse muitas outras perguntas relevantes.

As perguntas devem possuir diferentes níveis de dificuldade.

---

# Arquitetura

Quero que você proponha uma arquitetura altamente modular.

Gostaria que o projeto fosse dividido em componentes independentes.

Por exemplo:

- geração de dados
- renderização
- geração dos labels
- augmentations
- exportação
- validação
- configuração

---

# Escalabilidade

O sistema deve permitir adicionar facilmente novos tipos de documentos no futuro.

Não quero código específico para cada documento.

Prefiro um framework baseado em templates reutilizáveis.

---

# Entrega esperada

Antes de escrever qualquer código, elabore um documento contendo:

1. Arquitetura completa do projeto.
2. Organização das pastas.
3. Fluxo de geração.
4. Tecnologias recomendadas.
5. Bibliotecas recomendadas.
6. Estrutura dos templates.
7. Formato dos labels.
8. Estratégia para geração dos dados sintéticos.
9. Estratégia para evitar qualquer validade fiscal.
10. Estratégia para geração de VQA.
11. Estratégia para Layout Analysis.
12. Estratégia para OCR.
13. Estratégia para KIE.
14. Estratégia para expansão futura.
15. Possíveis dificuldades técnicas e soluções.

Não implemente nada ainda.

Primeiro quero validar o plano completo antes de iniciar o desenvolvimento.