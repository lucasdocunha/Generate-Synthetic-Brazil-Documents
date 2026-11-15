import random

import pytest

from generator import fake_data
from validation.schemas import ACCESS_KEY_RE, CNPJ_RE


def test_dv_cnpj_alfanumerico_exemplo_oficial_receita():
    # Exemplo da Receita Federal (IN RFB 2.229/2024): 12.ABC.345/01DE-35
    assert fake_data.cnpj_valid_dv("12ABC34501DE") == "35"


def test_dv_cnpj_numerico_inalterado():
    assert fake_data.cnpj_valid_dv("112223330001") == "81"


@pytest.mark.parametrize("alnum", [True, False])
def test_cnpj_formato_e_dv_corrompido(alnum):
    rng = random.Random(123)
    for _ in range(500):
        c = fake_data.cnpj(rng, alnum=alnum)
        assert CNPJ_RE.match(c), c
        assert fake_data.is_alnum_cnpj(c) is alnum
        # regra anti-validade: o DV final nunca é o correto
        assert c[12:] != fake_data.cnpj_valid_dv(c[:12])


@pytest.mark.parametrize("ratio", [0.0, 0.3, 1.0])
def test_fracao_alfanumerica(ratio):
    rng = random.Random(7)
    n = 5000
    frac = (
        sum(
            fake_data.is_alnum_cnpj(fake_data.cnpj(rng, alnum_ratio=ratio))
            for _ in range(n)
        )
        / n
    )
    assert abs(frac - ratio) < 0.03


def test_cnpj_reprodutivel_por_seed():
    a = [fake_data.cnpj(random.Random(99)) for _ in range(3)]
    b = [fake_data.cnpj(random.Random(99)) for _ in range(3)]
    assert a == b


def test_chave_com_cnpj_alfanumerico():
    rng = random.Random(1)
    cnpj = fake_data.cnpj(rng, alnum=True)
    chave = fake_data.access_key(
        rng, cnpj_digits=cnpj, serie="1", numero="123", emissao_aamm="2607"
    )
    assert len(chave) == 44
    assert ACCESS_KEY_RE.match(chave)
    assert chave[6:20] == cnpj
    assert chave[-1].isdigit()
    # DV correto (ord-48) existe, mas o gravado é sempre o corrompido
    assert int(chave[-1]) != fake_data.access_key_valid_dv(chave[:43])
