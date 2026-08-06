"""Tabelas de códigos fiscais (NCM/CFOP/CST).

PoC v0: conjunto pequeno e curado, extraído/inspirado nos XMLs de fixture já
existentes em tests/fixtures/ — suficiente para gerar DANFEs plausíveis e
estruturalmente coerentes.

Isso NÃO substitui a decisão registrada em PLANO_GERADOR.md (secao 5.1) de
usar a tabela oficial completa da Receita Federal/Siscomex mais adiante —
fica como follow-up explícito (importar via um script único, não em tempo de
geração), não uma regressão silenciosa da decisão.
"""

# categoria -> (variantes de descrição, prefixo de NCM plausível, CFOP interno)
PRODUCT_CATEGORIES = {
    "Parafuso": (["Aço inox", "Aço carbono", "Latão"], "7318", "5102"),
    "Cabo elétrico": (["100m", "50m", "10 AWG", "flexível"], "8544", "5102"),
    "Camiseta": (["Algodão", "Poliéster", "Dry-fit"], "6109", "5102"),
    "Cadeira": (["Escritório", "Gamer", "Plástica"], "9401", "5102"),
    "Flipover": (["Padrão", "Magnético"], "9610", "5102"),
    "Notebook": (["8GB RAM", "16GB RAM", "SSD 512GB"], "8471", "5102"),
    "Serviço de consultoria": (["mensal", "avulso"], "9999", "5102"),
    "Cimento": (["50kg", "25kg", "CP II"], "2523", "5102"),
}

# Ver nota no topo do arquivo: apenas CST 20 é suportado no template tpl_001
# (subárvore <ICMS20> fixa). Outras famílias exigem mais templates.
CST_ICMS_PROFILES = [
    {"cst": "20", "pRedBC": 0.0},
    {"cst": "20", "pRedBC": 30.0},
    {"cst": "20", "pRedBC": 51.11},
]
