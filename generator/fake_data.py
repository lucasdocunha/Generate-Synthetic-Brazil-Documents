"""Geradores de valores fake para o dataset sintético.

Todos os identificadores com dígito verificador (CPF, CNPJ, chave de acesso)
são gerados matematicamente válidos e então deliberadamente corrompidos no
último dígito verificador, por decisão de projeto registrada em
PLANO_GERADOR.md secao 9.1: isso garante, por construcao, que nenhum valor
gerado possa coincidir com um documento/CPF/CNPJ real (que sempre tem
checksum correto), sem depender de sorte estatistica.
"""

import random
from pathlib import Path

from faker import Faker

from generator import code_tables

_MUNICIPIOS_CSV = (
    Path(__file__).resolve().parent.parent
    / "renderers"
    / "danfse"
    / "municipios_ibge.csv"
)

# Nota importante: `validate_docbr` gera números usando `random.sample` do
# módulo `random` GLOBAL (não recebe um gerador seedado) — usá-lo para gerar
# quebraria a garantia de reprodutibilidade por seed (PLANO_GERADOR.md secao
# 3.2/15). Por isso os dígitos verificadores de CPF/CNPJ são implementados
# aqui mesmo (algoritmo mod-11 padrão), consumindo sempre do `rng` recebido.

_LEGAL_SUFFIXES = [
    ("LTDA", 0.45),
    ("ME", 0.2),
    ("EIRELI", 0.1),
    ("S.A.", 0.1),
    ("EPP", 0.1),
    ("MEI", 0.05),
]

_SECTOR_PREFIXES = [
    "Comércio de",
    "Indústria e Comércio de",
    "Distribuidora de",
    "Atacado de",
    "Serviços de",
    "Transportes",
    "Comercial",
]

_PRODUCT_CATEGORIES = code_tables.PRODUCT_CATEGORIES
_CST_ICMS_PROFILES = code_tables.CST_ICMS_PROFILES


def _corrupt_last_digit(digits: str) -> str:
    """Corrompe deliberadamente o último dígito verificador (mod-11 quebra)."""
    last = int(digits[-1])
    new_last = (last + 3) % 10
    if new_last == last:
        new_last = (last + 7) % 10
    return digits[:-1] + str(new_last)


def _char_value(c: str) -> int:
    """Valor de um caractere no cálculo do DV (IN RFB 2.229/2024): ord(c) - 48.
    Dígitos ficam inalterados (0-9) e letras viram A=17 ... Z=42."""
    return ord(c.upper()) - 48


def _mod11_dv(digits: str, weights) -> str:
    total = sum(_char_value(d) * w for d, w in zip(digits, weights))
    remainder = total % 11
    return "0" if remainder < 2 else str(11 - remainder)


_CNPJ_W1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
_CNPJ_W2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
_ALNUM = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
_LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

DEFAULT_CNPJ_ALNUM_RATIO = 0.3


def cnpj_valid_dv(base12: str) -> str:
    """Os 2 DVs corretos (sempre numéricos) para uma base de 12 caracteres
    [0-9A-Z] — vale tanto para CNPJ numérico quanto alfanumérico."""
    dv1 = _mod11_dv(base12, _CNPJ_W1)
    dv2 = _mod11_dv(base12 + dv1, _CNPJ_W2)
    return dv1 + dv2


def _cnpj_base12_alnum(rng: random.Random) -> str:
    raiz = [rng.choice(_ALNUM) for _ in range(8)]
    if not any(c.isalpha() for c in raiz):
        raiz[rng.randrange(8)] = rng.choice(_LETTERS)
    if rng.random() < 0.2:  # filial também alfanumérica
        ordem = "".join(rng.choice(_ALNUM) for _ in range(4))
    else:
        ordem = f"{rng.choice([1, 1, 1, 1, 2, 3]):04d}"
    return "".join(raiz) + ordem


def cnpj(rng: random.Random, alnum=None, alnum_ratio: float = DEFAULT_CNPJ_ALNUM_RATIO) -> str:
    """CNPJ de 14 posições com DV final corrompido.

    `alnum=None` sorteia o formato (alfanumérico com probabilidade
    `alnum_ratio`); True/False força. Formato alfanumérico (IN RFB
    2.229/2024): 12 primeiras posições em [0-9A-Z], 2 DVs numéricos.
    O sorteio do formato consome sempre 1 valor do rng, para manter a
    sequência estável entre ratios diferentes.
    """
    draw = rng.random()
    if alnum is None:
        alnum = draw < alnum_ratio
    if alnum:
        base12 = _cnpj_base12_alnum(rng)
    else:
        base12 = "".join(str(rng.randint(0, 9)) for _ in range(12))
    return _corrupt_last_digit(base12 + cnpj_valid_dv(base12))


def is_alnum_cnpj(value: str) -> bool:
    return any(c.isalpha() for c in value)


def cpf(rng: random.Random) -> str:
    """CPF de 11 dígitos, estruturalmente correto, com DV final corrompido."""
    base9 = "".join(str(rng.randint(0, 9)) for _ in range(9))
    dv1 = _mod11_dv(base9, [10, 9, 8, 7, 6, 5, 4, 3, 2])
    dv2 = _mod11_dv(base9 + dv1, [11, 10, 9, 8, 7, 6, 5, 4, 3, 2])
    valid = base9 + dv1 + dv2
    return _corrupt_last_digit(valid)


def access_key(
    rng: random.Random,
    *,
    cnpj_digits: str,
    serie: str,
    numero: str,
    emissao_aamm: str,
    modelo: str = "55",
    tp_emis: str = "1",
) -> str:
    """Chave de acesso de 44 posicoes (NFe/CTe/MDFe), com cUF fora da tabela
    IBGE real e digito verificador final corrompido - ver PLANO_GERADOR.md 9.2.

    `cnpj_digits` pode ser alfanumerico (NT 2025.001): as posicoes 7-20 da
    chave carregam letras e o DV usa o valor ord(c)-48 de cada caractere.
    O DV (cDV) continua sempre numerico.
    """
    cuf = "00"  # deliberadamente fora do intervalo real (11-53)
    c_nf = f"{rng.randint(0, 99999999):08d}"
    base43 = (
        cuf
        + emissao_aamm
        + cnpj_digits
        + modelo
        + f"{int(serie):03d}"
        + f"{int(numero):09d}"
        + tp_emis
        + c_nf
    )
    assert len(base43) == 43, len(base43)
    dv = _mod11_check_digit(base43)
    key43 = base43 + str(dv)
    return _corrupt_last_digit(key43)


def access_key_valid_dv(digits43: str) -> int:
    return _mod11_check_digit(digits43)


def _mod11_check_digit(digits43: str) -> int:
    weights = [2, 3, 4, 5, 6, 7, 8, 9]
    total = 0
    for i, ch in enumerate(reversed(digits43)):
        total += _char_value(ch) * weights[i % len(weights)]
    remainder = total % 11
    return 0 if remainder in (0, 1) else 11 - remainder


def company_name(rng: random.Random, faker: Faker) -> str:
    sector = rng.choice(_SECTOR_PREFIXES)
    core = faker.last_name()
    suffix = _weighted_choice(rng, _LEGAL_SUFFIXES)
    return f"{sector} {core} {suffix}"


def person_name(rng: random.Random, faker: Faker) -> str:
    return faker.name()


def _weighted_choice(rng: random.Random, options):
    values = [v for v, _ in options]
    weights = [w for _, w in options]
    return rng.choices(values, weights=weights, k=1)[0]


_MUNICIPIOS_CACHE = None


def _load_municipios():
    global _MUNICIPIOS_CACHE
    if _MUNICIPIOS_CACHE is None:
        rows = []
        with open(_MUNICIPIOS_CSV, encoding="utf8") as f:
            for line in f:
                cod, nome, uf = line.strip().split(";")
                rows.append((cod, nome, uf))
        _MUNICIPIOS_CACHE = rows
    return _MUNICIPIOS_CACHE


def load_municipios():
    return _load_municipios()


def address(rng: random.Random, faker: Faker) -> dict:
    cod, nome, uf = rng.choice(_load_municipios())
    return {
        "street": faker.street_name(),
        "number": str(rng.randint(1, 2000)),
        "complement": rng.choice(["", "Sala 12", "Ao lado do mercado", "Fundos", "Bloco B"]),
        "neighborhood": faker.bairro(),
        "municipality_code": cod,
        "municipality_name": nome,
        "uf": uf,
        "cep": f"{rng.randint(1000, 99999):05d}{rng.randint(0, 999):03d}",
    }


def phone_number(rng: random.Random, mobile: bool = True) -> str:
    ddd = rng.choice([11, 21, 31, 41, 51, 61, 71, 81, 85, 47, 48, 19])
    if mobile:
        return f"{ddd}9{rng.randint(0, 9999):04d}{rng.randint(0, 9999):04d}"
    return f"{ddd}{rng.randint(2000, 5999)}{rng.randint(0, 9999):04d}"


def email(faker: Faker) -> str:
    return faker.company_email()


def ie_stub(rng: random.Random) -> str:
    """Inscrição Estadual: nenhum dos 5 renderizadores valida/decodifica a IE
    (texto opaco), e o algoritmo de dígito verificador varia por UF (27
    algoritmos distintos) — para o PoC, apenas uma sequência de dígitos
    plausível, sem alegação de validade (PLANO_GERADOR.md 9.1, nota sobre IE).
    """
    return f"{rng.randint(0, 999999999999):012d}"


def product_line(rng: random.Random) -> dict:
    """Um item de linha de produto internamente consistente (PLANO_GERADOR.md 8.3).

    vProd = qCom * vUnCom; vICMS = vBC * pICMS; vPIS/vCOFINS analogos.
    """
    categoria = rng.choice(list(_PRODUCT_CATEGORIES.keys()))
    variantes, ncm_prefix, cfop = _PRODUCT_CATEGORIES[categoria]
    variante = rng.choice(variantes)
    descricao = f"{categoria} {variante}"
    ncm = f"{ncm_prefix}{rng.randint(0, 9999):04d}"

    qtd = round(rng.uniform(1, 50), 4)
    preco_unit = round(rng.uniform(5, 3000), 2)
    v_prod = round(qtd * preco_unit, 2)

    perfil = rng.choice(_CST_ICMS_PROFILES)
    p_red_bc = perfil["pRedBC"]
    v_bc = round(v_prod * (1 - p_red_bc / 100), 2)
    p_icms = rng.choice([0.0, 4.0, 7.0, 12.0, 18.0])
    v_icms = round(v_bc * p_icms / 100, 2)

    p_pis = 0.65
    v_pis = round(v_prod * p_pis / 100, 2)
    p_cofins = 3.0
    v_cofins = round(v_prod * p_cofins / 100, 2)

    return {
        "cProd": f"SKU{rng.randint(1000, 9999)}",
        "xProd": descricao,
        "NCM": ncm,
        "CFOP": cfop,
        "uCom": "UN",
        "qCom": f"{qtd:.4f}",
        "vUnCom": f"{preco_unit:.10f}",
        "vProd": f"{v_prod:.2f}",
        "CST": perfil["cst"],
        "pRedBC": f"{p_red_bc:.4f}",
        "vBC": f"{v_bc:.2f}",
        "pICMS": f"{p_icms:.4f}",
        "vICMS": f"{v_icms:.2f}",
        "vBC_pis_cofins": f"{v_prod:.2f}",
        "pPIS": f"{p_pis:.4f}",
        "vPIS": f"{v_pis:.2f}",
        "pCOFINS": f"{p_cofins:.4f}",
        "vCOFINS": f"{v_cofins:.2f}",
        # valores numéricos para agregação/consistência (não escritos no XML)
        "_qtd": qtd,
        "_preco_unit": preco_unit,
        "_v_prod": v_prod,
        "_v_bc": v_bc,
        "_v_icms": v_icms,
        "_v_pis": v_pis,
        "_v_cofins": v_cofins,
    }


def recent_datetime(rng: random.Random):
    import datetime

    days_ago = rng.randint(0, 3 * 365)
    dt = datetime.datetime(2023, 1, 1) + datetime.timedelta(
        days=days_ago, seconds=rng.randint(0, 86399)
    )
    return dt
