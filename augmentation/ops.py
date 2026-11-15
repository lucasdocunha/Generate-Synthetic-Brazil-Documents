"""Operações de augmentation curadas especificamente para documentos
escaneados/impressos (PLANO_GERADOR.md seção 4.2) — incluindo modos realistas
observados nos PDFs da Câmara dos Deputados:
- `clean_digital`: PDF/imagem digital limpa (ex.: 7438757.pdf);
- `color_scan`: scanner colorido com variação de papel/contraste/JPEG (ex.: 7381676.pdf, 5569594.pdf);
- `bw_binarized_scan`: scanner P&B binarizado com ruído salt-and-pepper (ex.: 6436820.pdf, 6045314.pdf).
"""

import random

import albumentations as A
import cv2
import numpy as np
from PIL import Image

GEOMETRIC = A.Affine(
    rotate=(-3.5, 3.5),
    translate_percent=0.0,
    scale=1.0,
    shear=0,
    fit_output=True,
    p=0.7,
)

NON_GEOMETRIC = A.Compose(
    [
        A.GaussNoise(std_range=(0.02, 0.07), p=0.35),
        A.OneOf(
            [
                A.GaussianBlur(blur_limit=(3, 5), p=1.0),
                A.MotionBlur(blur_limit=(3, 5), p=1.0),
            ],
            p=0.2,
        ),
        A.RandomBrightnessContrast(brightness_limit=0.14, contrast_limit=0.14, p=0.45),
        A.Downscale(scale_range=(0.55, 0.85), p=0.15),
        A.ImageCompression(quality_range=(40, 82), p=0.35),
    ]
)


def apply_bw_binarized_scan(image: Image.Image, rng: random.Random) -> Image.Image:
    """Simula scanner P&B binarizado com pontilhados (ref. PDFs 6436820 e 6045314)."""
    gray = np.array(image.convert("L"))
    h, w = gray.shape
    np_rng = np.random.default_rng(rng.randint(0, 2**31 - 1))

    # Leve blur antes do threshold para engrossar/unir serifa como em fax/scanner 200dpi
    if rng.random() < 0.6:
        gray = cv2.GaussianBlur(gray, (3, 3), 0.6)

    block_size = rng.choice([21, 31, 41])
    c_val = rng.uniform(8.0, 15.0)
    bw = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, block_size, c_val
    )

    # Pontilhados pretos esparsos (pepper noise típico de cilindro/vidro de scanner)
    pepper_rate = rng.uniform(0.0004, 0.0018)
    pepper = np_rng.random((h, w)) < pepper_rate
    bw[pepper] = 0

    # Micro-falhas brancas no texto (salt noise leve)
    salt_rate = rng.uniform(0.0003, 0.0012)
    salt = np_rng.random((h, w)) < salt_rate
    bw[salt] = 255

    rgb = np.stack([bw, bw, bw], axis=-1)
    return Image.fromarray(rgb)


def apply_color_scan(image: Image.Image, rng: random.Random, seed: int = None) -> Image.Image:
    """Simula scanner colorido com leve tom de papel e compressão."""
    arr = np.array(image.convert("RGB")).astype(np.float32)
    # Leve tint de papel (creme/amarelado ou cinza-azulado frio)
    tint = rng.choice([(1.0, 0.99, 0.96), (0.98, 0.98, 0.99), (0.99, 0.98, 0.95)])
    arr[:, :, 0] *= tint[0]
    arr[:, :, 1] *= tint[1]
    arr[:, :, 2] *= tint[2]
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    if seed is not None:
        NON_GEOMETRIC.set_random_seed(seed % (2**31 - 1))
    res = NON_GEOMETRIC(image=arr)["image"]
    return Image.fromarray(res)
