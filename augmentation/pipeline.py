"""Pipeline de augmentation seedável (PLANO_GERADOR.md secao 4.2/15).

Decisão de projeto: a imagem "limpa" (só augmentations não-geométricos, que
nunca movem pixels e por isso nunca invalidam bbox) é a que carrega o label
canônico; a variante geométrica (rotação leve) é um "irmão" de robustez
adicional, com boxes explicitamente não-garantidas — evita todo o trabalho
de reprojeção de coordenadas ao custo de não ter bbox exata na variante
rotacionada (trade-off assumido explicitamente, não escondido).
"""

import random as _random

import numpy as np

from augmentation.ops import GEOMETRIC, NON_GEOMETRIC


def _seed_all(seed):
    if seed is not None:
        _random.seed(seed)
        np.random.seed(seed % (2**32))


def augment_clean(image, seed=None):
    """Aplica só augmentations não-geométricos — a imagem que carrega o label."""
    _seed_all(seed)
    arr = np.array(image.convert("RGB"))
    result = NON_GEOMETRIC(image=arr)
    from PIL import Image

    return Image.fromarray(result["image"]), {"seed": seed, "ops": "non_geometric"}


def augment_geometric_variant(image, seed=None):
    """Variante adicional de robustez com rotação leve — boxes NÃO garantidas."""
    _seed_all((seed or 0) + 1)
    arr = np.array(image.convert("RGB"))
    result = GEOMETRIC(image=arr)
    from PIL import Image

    return Image.fromarray(result["image"]), {"seed": seed, "ops": "geometric", "boxes_valid": False}
