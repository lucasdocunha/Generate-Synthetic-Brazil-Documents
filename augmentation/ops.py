"""Operações de augmentation curadas especificamente para documentos
escaneados/impressos (PLANO_GERADOR.md secao 4.2) — deliberadamente NÃO usa
presets de foto (sem hue/flip/cutout, sem análogo em captura de documento
real). Separadas em geométricas (invalidam bbox) e não-geométricas (não
invalidam) — ver PLANO_GERADOR.md secao 15, "coordenadas sob augmentation".
"""

import albumentations as A

GEOMETRIC = A.Affine(
    rotate=(-3, 3),
    translate_percent=0.0,
    scale=1.0,
    shear=0,
    fit_output=True,
    p=0.5,
)

NON_GEOMETRIC = A.Compose(
    [
        A.GaussNoise(std_range=(0.02, 0.08), p=0.3),
        A.OneOf(
            [
                A.GaussianBlur(blur_limit=(3, 5), p=1.0),
                A.MotionBlur(blur_limit=(3, 5), p=1.0),
            ],
            p=0.2,
        ),
        A.RandomBrightnessContrast(brightness_limit=0.15, contrast_limit=0.15, p=0.4),
        A.Downscale(scale_range=(0.5, 0.8), p=0.15),
        A.ImageCompression(quality_range=(35, 80), p=0.3),
    ]
)
