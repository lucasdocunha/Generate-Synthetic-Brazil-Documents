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


# --- Diversidade estrutural da NF-e (perfil sorteado em generator/nfe_profile.py) ---

# Categorias com grupos específicos de item: `kind` decide se o item ganha
# <comb> (ANP), <med> (ANVISA) + <rastro>, ou é um serviço (ISSQN).
SPECIAL_PRODUCT_CATEGORIES = {
    "Óleo diesel": {
        "variants": ["S10", "S500"], "ncm_prefix": "2710", "cfop": "5656",
        "unit": "L", "kind": "anp",
        "anp": [("820101034", "OLEO DIESEL B S10 - COMUM"), ("820101012", "OLEO DIESEL B S500 - COMUM")],
    },
    "Gasolina": {
        "variants": ["comum", "aditivada"], "ncm_prefix": "2710", "cfop": "5656",
        "unit": "L", "kind": "anp",
        "anp": [("320102001", "GASOLINA C COMUM"), ("320102002", "GASOLINA C ADITIVADA")],
    },
    "Dipirona sódica": {
        "variants": ["500mg 10 comp", "1g 10 comp", "gotas 20ml"], "ncm_prefix": "3004",
        "cfop": "5102", "unit": "CX", "kind": "anvisa",
    },
    "Amoxicilina": {
        "variants": ["500mg 21 caps", "875mg 14 comp"], "ncm_prefix": "3004",
        "cfop": "5102", "unit": "CX", "kind": "anvisa",
    },
    "Serviço de instalação": {
        "variants": ["elétrica", "hidráulica", "de equipamento"], "ncm_prefix": "0000",
        "cfop": "5933", "unit": "SV", "kind": "service", "cListServ": "14.06",
    },
    "Serviço de manutenção": {
        "variants": ["preventiva", "corretiva"], "ncm_prefix": "0000",
        "cfop": "5933", "unit": "SV", "kind": "service", "cListServ": "14.01",
    },
}

UNITS = ["UN", "UN", "UN", "PC", "CX", "KG", "M", "LT", "PCT", "DZ"]

# Regime normal (CRT 3): CST do ICMS -> grupo XML e campos que ele carrega.
ICMS_CST_GROUPS = {
    "00": {"tag": "ICMS00", "bc": True, "st": False, "red": False},
    "10": {"tag": "ICMS10", "bc": True, "st": True, "red": False},
    "20": {"tag": "ICMS20", "bc": True, "st": False, "red": True},
    "40": {"tag": "ICMS40", "bc": False, "st": False, "red": False},
    "41": {"tag": "ICMS40", "bc": False, "st": False, "red": False},
    "60": {"tag": "ICMS60", "bc": False, "st": False, "red": False},
    "90": {"tag": "ICMS90", "bc": True, "st": False, "red": False},
}

# Simples Nacional / MEI (CRT 1 ou 4): CSOSN -> grupo XML.
CSOSN_GROUPS = {
    "101": {"tag": "ICMSSN101", "credit": True},
    "102": {"tag": "ICMSSN102", "credit": False},
    "103": {"tag": "ICMSSN102", "credit": False},
    "300": {"tag": "ICMSSN102", "credit": False},
    "400": {"tag": "ICMSSN102", "credit": False},
    "500": {"tag": "ICMSSN500", "credit": False},
    "900": {"tag": "ICMSSN900", "credit": False},
}

TP_PAG = ["01", "03", "04", "15", "17", "99"]  # dinheiro, crédito, débito, boleto, PIX, outros

ESPECIES_VOLUME = ["CAIXA", "VOLUME", "PALLET", "FARDO", "SACO", "PACOTE"]

INF_CPL_SENTENCES = [
    "Documento emitido por ME ou EPP optante pelo Simples Nacional.",
    "Não gera direito a crédito fiscal de IPI.",
    "Pedido de compra nº {n}.",
    "Mercadoria entregue conforme pedido {n}.",
    "Vendedor: {nome}.",
    "Valor aproximado dos tributos conforme Lei 12.741/2012.",
    "Retenção de PIS/COFINS/CSLL conforme legislação vigente.",
    "Prazo para reclamação de avarias: 7 dias após o recebimento.",
    "Referente ao contrato {n}.",
    "Local de entrega diferente do endereço do destinatário.",
]
