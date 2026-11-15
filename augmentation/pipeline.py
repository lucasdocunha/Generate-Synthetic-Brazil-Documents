"""Pipeline de augmentation seedável com reprojeção exata de bounding boxes
sob rotação e composição de artefatos físicos (carimbos, assinaturas, POS, riscos).
"""

import copy
import random as _random

import cv2
import numpy as np
from PIL import Image

from augmentation.ops import GEOMETRIC, NON_GEOMETRIC, apply_bw_binarized_scan, apply_color_scan
from augmentation.stamps import compose_document_artifacts


def _seed_all(seed):
    if seed is not None:
        _random.seed(seed)
        np.random.seed(seed % (2**32))
        s31 = int(seed % (2**31 - 1))
        NON_GEOMETRIC.set_random_seed(s31)
        GEOMETRIC.set_random_seed(s31)


def transform_bbox_mm(bbox: dict, M_mm: np.ndarray, page_w_mm: float, page_h_mm: float) -> dict:
    """Aplica matriz afim 2x3 (em mm) aos 4 cantos de `bbox` e retorna o novo
    envelope alinhado aos eixos + `obb_points` (4 vértices rotacionados).
    """
    x0, y0 = float(bbox["x"]), float(bbox["y"])
    w, h = float(bbox["w"]), float(bbox["h"])
    corners = np.array(
        [
            [x0, y0, 1.0],
            [x0 + w, y0, 1.0],
            [x0 + w, y0 + h, 1.0],
            [x0, y0 + h, 1.0],
        ],
        dtype=np.float64,
    )
    rot_pts = (M_mm @ corners.T).T  # (4, 2)
    xs = np.clip(rot_pts[:, 0], 0.0, page_w_mm)
    ys = np.clip(rot_pts[:, 1], 0.0, page_h_mm)
    nx0, ny0 = float(xs.min()), float(ys.min())
    nw = max(0.05, float(xs.max() - nx0))
    nh = max(0.05, float(ys.max() - ny0))
    return {
        "x": round(nx0, 3),
        "y": round(ny0, 3),
        "w": round(nw, 3),
        "h": round(nh, 3),
        "unit": "mm",
        "obb_points": [[round(float(px), 3), round(float(py), 3)] for px, py in rot_pts],
    }


def rotate_image_and_reproject_label(
    image: Image.Image,
    label: dict,
    angle_deg: float,
    rng: _random.Random = None,
    page_number: int = 1,
) -> tuple[Image.Image, dict]:
    """Rotaciona a imagem por `angle_deg` e reprojeta todas as `bbox` de
    `elements[]` e `layout["special_objects"]` da página correspondente.
    """
    if abs(angle_deg) < 1e-3:
        return image, label

    rng = rng or _random.Random(0)
    arr = np.array(image.convert("RGB"))
    h_px, w_px = arr.shape[:2]
    M_px = cv2.getRotationMatrix2D((w_px / 2.0, h_px / 2.0), angle_deg, 1.0)
    border_val = (32, 32, 35) if rng.random() < 0.55 else (246, 246, 246)
    warped = cv2.warpAffine(
        arr,
        M_px,
        (w_px, h_px),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=border_val,
    )

    page_info = next(
        (p for p in label.get("pages", []) if p.get("page_number") == page_number),
        {"size_mm": {"w": 210.0, "h": 297.0}},
    )
    w_mm = page_info["size_mm"]["w"]
    h_mm = page_info["size_mm"]["h"]
    M_mm = cv2.getRotationMatrix2D((w_mm / 2.0, h_mm / 2.0), angle_deg, 1.0)

    new_label = copy.deepcopy(label)
    for el in new_label.get("elements", []):
        if el.get("page") == page_number and "bbox" in el:
            el["bbox"] = transform_bbox_mm(el["bbox"], M_mm, w_mm, h_mm)

    for obj in new_label.get("layout", {}).get("special_objects", []):
        if obj.get("page") == page_number and "bbox" in obj:
            obj["bbox"] = transform_bbox_mm(obj["bbox"], M_mm, w_mm, h_mm)

    return Image.fromarray(warped), new_label


def augment_document(
    image: Image.Image,
    label: dict,
    field_values: dict,
    seed: int = None,
    artifact_preset: str = None,
    scan_mode: str = None,
    angle_deg: float = None,
    tilt_deg: float = None,
) -> tuple[Image.Image, dict, dict]:
    """Pipeline unificado:
    1. Sobrepõe carimbos, assinaturas, comprovante POS e riscos, adicionando
       seus bboxes em `label["layout"]["special_objects"]`;
    2. Rotaciona ("deixa um pouco de lado") e reprojeta todas as bboxes em `mm`;
    3. Aplica modo fotométrico de scanner (`clean_digital`, `color_scan`, `bw_binarized_scan`).
    """
    if angle_deg is None and tilt_deg is not None:
        angle_deg = tilt_deg
    _seed_all(seed)
    rng = _random.Random(seed)

    page_size_mm = (
        label["pages"][0]["size_mm"]
        if label.get("pages")
        else {"w": 210.0, "h": 297.0}
    )

    img_art, added_objs = compose_document_artifacts(
        image, field_values, page_size_mm, rng, preset=artifact_preset
    )
    updated_label = copy.deepcopy(label)
    updated_label.setdefault("layout", {}).setdefault("special_objects", []).extend(added_objs)

    if angle_deg is None:
        # 65% das notas têm leve inclinação (-3.8° a +3.8°, evitando ângulo ~0)
        if rng.random() < 0.65:
            sign = -1.0 if rng.random() < 0.5 else 1.0
            angle_deg = round(sign * rng.uniform(0.7, 3.8), 2)
        else:
            angle_deg = 0.0

    img_rot, updated_label = rotate_image_and_reproject_label(
        img_art, updated_label, angle_deg, rng=rng, page_number=1
    )

    if scan_mode is None:
        scan_mode = rng.choices(
            ["clean_digital", "color_scan", "bw_binarized_scan"],
            weights=[0.20, 0.48, 0.32],
            k=1,
        )[0]

    if scan_mode == "bw_binarized_scan":
        img_final = apply_bw_binarized_scan(img_rot, rng)
    elif scan_mode == "color_scan":
        img_final = apply_color_scan(img_rot, rng, seed=seed)
    else:
        img_final = img_rot

    aug_meta = {
        "seed": seed,
        "angle_deg": angle_deg,
        "scan_mode": scan_mode,
        "special_objects_added": [o["type"] for o in added_objs],
        "boxes_valid": True,
    }
    return img_final, updated_label, aug_meta


def augment_clean(image, seed=None):
    """Compatibilidade legada: aplica só augmentations não-geométricos."""
    _seed_all(seed)
    arr = np.array(image.convert("RGB"))
    result = NON_GEOMETRIC(image=arr)
    return Image.fromarray(result["image"]), {"seed": seed, "ops": "non_geometric"}


def augment_geometric_variant(image, seed=None):
    """Compatibilidade legada: variante geométrica via Albumentations."""
    _seed_all((seed or 0) + 1)
    arr = np.array(image.convert("RGB"))
    result = GEOMETRIC(image=arr)
    return Image.fromarray(result["image"]), {"seed": seed, "ops": "geometric", "boxes_valid": False}
