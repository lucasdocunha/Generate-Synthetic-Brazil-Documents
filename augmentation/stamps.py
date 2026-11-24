"""Artefatos físicos realistas para documentos fiscais:
- Carimbos de borracha (`receipt_stamp`, `cnpj_stamp`, `status_stamp`) com
  desgaste/porosidade de tinta, data manuscrita e rubrica;
- Assinaturas/rubricas manuscritas (`signature`) via recortes de `Teste2.png`
  e curvas Bézier caligráficas;
- Comprovantes térmicos de cartão/POS (`pos_receipt`: Getnet, Rede, Cielo, Stone)
  sobrepostos à nota (ref. PDF 6436820);
- Riscos de caneta, marcas de conferência, dobras e bordas de scanner.

Todas as funções retornam a imagem composta e as entradas correspondentes para
`layout["special_objects"]` com `bbox` em milímetros.
"""

import math
from pathlib import Path
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from renderers.utils import format_cep, format_cpf_cnpj

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SIGNATURE_SHEET = _REPO_ROOT / "Teste2.png"
_SIG_CROPS_CACHE = None

_FONTS = {
    "sans_bold": [
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ],
    "sans": [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ],
    "serif_bold": [
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
    ],
    "mono": [
        "/usr/share/fonts/truetype/ubuntu/UbuntuMono-R.ttf",
        "/usr/share/fonts/truetype/freefont/FreeMono.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    ],
    "hand": [
        "/usr/share/fonts/truetype/tlwg/Purisa-BoldOblique.ttf",
        "/usr/share/fonts/truetype/tlwg/Purisa-Oblique.ttf",
        "/usr/share/fonts/truetype/tlwg/Purisa.ttf",
    ],
}

_STAMP_COLORS = [
    (38, 72, 145),   # Azul carimbo clássico (7381676.pdf)
    (52, 88, 168),   # Azul claro desbotado
    (35, 38, 45),    # Preto acinzentado (5569594.pdf)
    (78, 38, 105),   # Violeta/roxo de almofada de carimbo
    (138, 35, 35),   # Vermelho escuro ("PAGO"/"CONFERIDO")
]

_PEN_COLORS = [
    (22, 52, 135),   # Caneta esferográfica azul
    (35, 70, 160),   # Caneta azul clara
    (28, 28, 32),    # Caneta preta
]


def _font(family: str, size: int):
    for p in _FONTS.get(family, []):
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, size=size)
            except OSError:
                pass
    return ImageFont.load_default(size=size)


def _load_signature_crops():
    """Extrai as 3 faixas de assinatura manuscrita de `Teste2.png`."""
    global _SIG_CROPS_CACHE
    if _SIG_CROPS_CACHE is not None:
        return _SIG_CROPS_CACHE
    crops = []
    if _SIGNATURE_SHEET.exists():
        try:
            sheet = Image.open(_SIGNATURE_SHEET).convert("L")
            w, h = sheet.size
            bands = [(0, int(h * 0.36)), (int(h * 0.36), int(h * 0.70)), (int(h * 0.70), h)]
            for y0, y1 in bands:
                band = sheet.crop((0, y0, w, y1))
                arr = np.array(band)
                mask = arr < 200
                if mask.any():
                    ys, xs = np.where(mask)
                    sub = arr[ys.min() : ys.max() + 1, xs.min() : xs.max() + 1]
                    crops.append(sub)
        except OSError:
            pass
    _SIG_CROPS_CACHE = crops
    return crops


def _apply_ink_wear(rgba_img: Image.Image, rng: random.Random, fade_range=(0.45, 0.88)) -> Image.Image:
    """Simula falha de pressão e textura porosa de carimbo de borracha."""
    arr = np.array(rgba_img).astype(np.float32)
    h, w, _ = arr.shape
    np_rng = np.random.default_rng(rng.randint(0, 2**31 - 1))

    # Ruído em duas escalas (granulação fina + falha de pressão regional)
    coarse = np_rng.uniform(0.45, 1.05, size=(max(4, h // 18), max(4, w // 18))).astype(np.float32)
    coarse_img = Image.fromarray((coarse * 255).astype(np.uint8)).resize((w, h), Image.Resampling.BILINEAR)
    coarse_map = np.array(coarse_img).astype(np.float32) / 255.0

    fine = np_rng.uniform(0.65, 1.0, size=(h, w)).astype(np.float32)
    # Gradiente linear leve (carimbo pressionado mais forte de um lado)
    gx = np.linspace(rng.uniform(0.6, 1.0), rng.uniform(0.6, 1.0), w, dtype=np.float32)
    gy = np.linspace(rng.uniform(0.7, 1.0), rng.uniform(0.7, 1.0), h, dtype=np.float32)
    grad = np.outer(gy, gx)

    base_fade = rng.uniform(*fade_range)
    alpha_mult = np.clip(coarse_map * fine * grad * base_fade, 0.0, 1.0)
    arr[:, :, 3] = arr[:, :, 3] * alpha_mult
    return Image.fromarray(arr.astype(np.uint8))


def _draw_bezier_signature(draw: ImageDraw.ImageDraw, box, rng: random.Random, color):
    x0, y0, x1, y1 = box
    w = x1 - x0
    h = y1 - y0
    cx = x0 + w * 0.12
    cy = y0 + h * 0.6
    pts = [(cx, cy)]
    n_loops = rng.randint(6, 12)
    for i in range(n_loops):
        t = (i + 1) / n_loops
        nx = x0 + w * (0.12 + 0.78 * t) + rng.uniform(-w * 0.06, w * 0.06)
        ny = y0 + h * rng.uniform(0.18, 0.85)
        pts.append((nx, ny))
    # Subdivide por interpolação catmull/quadrática simples
    smooth = []
    for i in range(len(pts) - 1):
        p0 = pts[max(0, i - 1)]
        p1 = pts[i]
        p2 = pts[i + 1]
        p3 = pts[min(len(pts) - 1, i + 2)]
        for step in range(12):
            u = step / 12.0
            u2 = u * u
            u3 = u2 * u
            x = 0.5 * (
                (2 * p1[0])
                + (-p0[0] + p2[0]) * u
                + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * u2
                + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * u3
            )
            y = 0.5 * (
                (2 * p1[1])
                + (-p0[1] + p2[1]) * u
                + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * u2
                + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * u3
            )
            smooth.append((x, y))
    if len(smooth) > 1:
        draw.line(smooth, fill=color, width=rng.randint(2, 3), joint="curve")
    # Traço de corte/rubrica final
    draw.line(
        [(x0 + w * 0.18, y0 + h * 0.72), (x0 + w * 0.86, y0 + h * 0.45)],
        fill=color,
        width=2,
    )


def render_signature_layer(rng: random.Random, width_px: int = 260, height_px: int = 95) -> Image.Image:
    """Retorna imagem RGBA de assinatura/rubrica à caneta."""
    pen_rgb = rng.choice(_PEN_COLORS)
    crops = _load_signature_crops()
    if crops and rng.random() < 0.65:
        crop = rng.choice(crops)
        ch, cw = crop.shape
        scale = min(width_px / cw, height_px / ch) * rng.uniform(0.82, 0.98)
        nw, nh = max(20, int(cw * scale)), max(12, int(ch * scale))
        resized = Image.fromarray(crop).resize((nw, nh), Image.Resampling.BICUBIC)
        arr = np.array(resized)
        alpha = np.clip((235 - arr.astype(np.int32)) * 1.6, 0, 240).astype(np.uint8)
        rgba = np.zeros((height_px, width_px, 4), dtype=np.uint8)
        ox = (width_px - nw) // 2
        oy = (height_px - nh) // 2
        rgba[oy : oy + nh, ox : ox + nw, 0] = pen_rgb[0]
        rgba[oy : oy + nh, ox : ox + nw, 1] = pen_rgb[1]
        rgba[oy : oy + nh, ox : ox + nw, 2] = pen_rgb[2]
        rgba[oy : oy + nh, ox : ox + nw, 3] = alpha
        img = Image.fromarray(rgba)
    else:
        img = Image.new("RGBA", (width_px, height_px), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        _draw_bezier_signature(draw, (8, 8, width_px - 8, height_px - 8), rng, (*pen_rgb, 225))
    angle = rng.uniform(-7.0, 7.0)
    return img.rotate(angle, expand=True, resample=Image.Resampling.BICUBIC)


def render_receipt_stamp(
    rng: random.Random,
    company_name: str,
    date_br: str = "27/04/2024",
    style: str = None,
) -> Image.Image:
    """Gera carimbo de recebimento/conferência (ref. 7381676.pdf e 5569594.pdf)."""
    style = style or rng.choice(["blue_recebemos", "classic_em_de", "status_box"])
    stamp_rgb = rng.choice(_STAMP_COLORS[:4] if style != "status_box" else _STAMP_COLORS)
    pen_rgb = rng.choice(_PEN_COLORS)
    parts = date_br.split("/")
    dd = parts[0] if len(parts) == 3 else "15"
    mm = parts[1] if len(parts) == 3 else "08"
    yy = parts[2][-2:] if len(parts) == 3 else "24"
    yyyy = parts[2] if len(parts) == 3 else "2024"

    transcript: list[str] = []
    if style == "blue_recebemos":
        transcript = ["RECEBEMOS", f"{dd}/{mm}/{yy}", company_name.upper()[:34]]
        # Estilo 7381676.pdf: RECEBEMOS grande + data __/__/__ + assinatura + empresa na base
        w, h = 420, 210
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        col = (*stamp_rgb, 235)
        draw.text((w // 2, 28), "RECEBEMOS", fill=col, font=_font("sans_bold", 42), anchor="mm")
        draw.text((w // 2, 86), "____/____/____", fill=col, font=_font("sans_bold", 30), anchor="mm")
        draw.line((28, 156, w - 28, 156), fill=col, width=3)
        draw.text(
            (w // 2, 182),
            company_name.upper()[:34],
            fill=col,
            font=_font("sans_bold", 18),
            anchor="mm",
        )
        img = _apply_ink_wear(img, rng, fade_range=(0.55, 0.88))
        # Preenchimento à caneta (data + rubrica)
        draw_pen = ImageDraw.Draw(img)
        f_hand = _font("hand", 26)
        pcol = (*pen_rgb, 230)
        draw_pen.text((132, 74), dd, fill=pcol, font=f_hand, anchor="mm")
        draw_pen.text((210, 74), mm, fill=pcol, font=f_hand, anchor="mm")
        draw_pen.text((290, 74), yy, fill=pcol, font=f_hand, anchor="mm")
        sig = render_signature_layer(rng, width_px=240, height_px=75)
        img.alpha_composite(sig, dest=(90, 92))

    elif style == "classic_em_de":
        transcript = ["Recebemos", f"Em {dd} de {mm} de {yyyy[:3]}{yy[-1]}"]
        # Estilo 5569594.pdf: "Recebemos / Em __ de __ de 20__ / [rubrica]"
        w, h = 390, 195
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        col = (*stamp_rgb, 240)
        draw.text((w // 2, 26), "Recebemos", fill=col, font=_font("serif_bold", 34), anchor="mm")
        draw.text(
            (w // 2, 70),
            f"Em ____ de ________ de {yyyy[:3]}__",
            fill=col,
            font=_font("serif_bold", 20),
            anchor="mm",
        )
        draw.line((35, 145, w - 35, 145), fill=col, width=3)
        img = _apply_ink_wear(img, rng, fade_range=(0.60, 0.92))
        draw_pen = ImageDraw.Draw(img)
        f_hand = _font("hand", 22)
        pcol = (*pen_rgb, 235)
        draw_pen.text((104, 62), dd, fill=pcol, font=f_hand, anchor="mm")
        draw_pen.text((212, 62), mm, fill=pcol, font=f_hand, anchor="mm")
        draw_pen.text((342, 62), yy[-1], fill=pcol, font=f_hand, anchor="mm")
        sig = render_signature_layer(rng, width_px=230, height_px=80)
        img.alpha_composite(sig, dest=(80, 88))

    else:
        # Carimbo retangular de status ("PAGO", "CONFERIDO", "LANÇADO")
        w, h = 320, 130
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        col = (*stamp_rgb, 230)
        label = rng.choice(["PAGO", "CONFERIDO", "LANÇADO", " LIQUIDADO "])
        draw.rectangle((10, 10, w - 10, h - 10), outline=col, width=5)
        draw.rectangle((17, 17, w - 17, h - 17), outline=col, width=2)
        transcript = [label.strip(), f"DATA: {date_br}"]
        draw.text((w // 2, 48), label, fill=col, font=_font("sans_bold", 34), anchor="mm")
        draw.text((w // 2, 92), f"DATA: {date_br}", fill=col, font=_font("sans_bold", 18), anchor="mm")
        img = _apply_ink_wear(img, rng, fade_range=(0.50, 0.85))

    angle = rng.uniform(-11.0, 11.0)
    out = img.rotate(angle, expand=True, resample=Image.Resampling.BICUBIC)
    out.info["transcript"] = transcript
    return out


def render_cnpj_stamp(
    rng: random.Random,
    cnpj_raw: str,
    company_name: str,
    address: dict,
) -> Image.Image:
    """Carimbo societário de CNPJ com cantoneiras (ref. PDF 7381676)."""
    w, h = 430, 215
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    stamp_rgb = rng.choice(_STAMP_COLORS[:3])
    col = (*stamp_rgb, 225)

    # Cantoneiras nos 4 cantos (exatamente como no PDF 7381676)
    m, clen = 12, 26
    draw.line([(m, m + clen), (m, m), (m + clen, m)], fill=col, width=4)
    draw.line([(w - m - clen, m), (w - m, m), (w - m, m + clen)], fill=col, width=4)
    draw.line([(m, h - m - clen), (m, h - m), (m + clen, h - m)], fill=col, width=4)
    draw.line([(w - m - clen, h - m), (w - m, h - m), (w - m, h - m - clen)], fill=col, width=4)

    cnpj_fmt = format_cpf_cnpj(cnpj_raw)
    draw.text((w // 2, 42), f"[{cnpj_fmt}]", fill=col, font=_font("sans_bold", 30), anchor="mm")
    draw.text(
        (w // 2, 86),
        company_name.upper()[:30],
        fill=col,
        font=_font("sans_bold", 20),
        anchor="mm",
    )
    street_line = f"{address.get('street', 'AV. CENTRAL')}, {address.get('number', '100')}".upper()[:34]
    bairro_cep = f"{address.get('neighborhood', 'CENTRO')} - CEP {format_cep(address.get('cep', '70000000'))}".upper()[:36]
    mun_uf = f"{address.get('municipality_name', 'BRASILIA')} - {address.get('uf', 'DF')}".upper()[:32]
    f_addr = _font("sans", 16)
    draw.text((w // 2, 122), street_line, fill=col, font=f_addr, anchor="mm")
    draw.text((w // 2, 148), bairro_cep, fill=col, font=f_addr, anchor="mm")
    draw.text((w // 2, 174), mun_uf, fill=col, font=_font("sans_bold", 17), anchor="mm")

    img = _apply_ink_wear(img, rng, fade_range=(0.38, 0.76))
    angle = rng.uniform(-6.5, 6.5)
    out = img.rotate(angle, expand=True, resample=Image.Resampling.BICUBIC)
    out.info["transcript"] = [f"[{cnpj_fmt}]", company_name.upper()[:30], street_line, bairro_cep, mun_uf]
    return out


def render_pos_receipt(
    rng: random.Random,
    cnpj_raw: str,
    company_name: str,
    address: dict,
    date_br: str,
    valor_nf: float,
) -> Image.Image:
    """Gera comprovante térmico de cartão (POS Getnet/Rede/Cielo/Stone, ref. 6436820.pdf)."""
    w, h = 340, 430
    img = Image.new("RGBA", (w + 16, h + 16), (0, 0, 0, 0))
    # Sombra leve do papel sobreposto
    shadow = Image.new("RGBA", (w, h), (30, 30, 30, 55))
    img.paste(shadow, (10, 10))
    img = img.filter(ImageFilter.GaussianBlur(radius=3))

    paper_tint = rng.choice([(248, 246, 236, 252), (244, 245, 247, 252), (250, 244, 228, 252)])
    slip = Image.new("RGBA", (w, h), paper_tint)
    draw = ImageDraw.Draw(slip)
    draw.rectangle((0, 0, w - 1, h - 1), outline=(170, 170, 165, 220), width=1)

    acquirer = rng.choice(["getnet", "rede", "cielo", "stone"])
    brand = rng.choice(["ELO", "VISA", "MASTERCARD"])
    mode = rng.choice(["DEBITO A VISTA", "CREDITO A VISTA"])
    cnpj_fmt = format_cpf_cnpj(cnpj_raw)
    val_fmt = f"{valor_nf:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    ink = (32, 32, 35, 235)
    f_logo = _font("sans_bold", 34)
    f_mono = _font("mono", 15)
    f_mono_b = _font("mono", 17)

    draw.text((w // 2, 38), acquirer, fill=ink, font=f_logo, anchor="mm")
    draw.text((w // 2, 70), f"REDE {acquirer.upper()} - Via Cliente", fill=ink, font=f_mono, anchor="mm")

    lines = [
        company_name.upper()[:28],
        f"{address.get('street', 'RUA PRINCIPAL')[:22].upper()} {address.get('number', '100')}",
        f"{address.get('municipality_name', 'CUIABA')[:20].upper()} - {address.get('uf', 'MT')}",
        f"{cnpj_fmt} CV:{rng.randint(10000000, 99999999)}",
        f"{date_br} {rng.randint(8, 20):02d}:{rng.randint(0, 59):02d}:{rng.randint(0, 59):02d} AUT:{rng.randint(100000, 999999)}",
        f"DOC:{rng.randint(100000, 999999)} TERM:0{rng.randint(100000, 999999)}",
        f"{brand}            ************{rng.randint(1000, 9999)}",
        f"CVAD:{rng.randint(100000, 999999)}",
        f"        {mode}",
        f"VALOR:         {val_fmt}",
    ]
    y = 104
    for ln in lines:
        font_use = f_mono_b if "VALOR:" in ln or mode in ln else f_mono
        draw.text((28, y), ln, fill=ink, font=font_use)
        y += 26

    # Textos verticais nas bordas laterais do comprovante (como no Getnet de 6436820.pdf)
    side_img = Image.new("RGBA", (220, 22), (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(side_img)
    sdraw.text((4, 2), "EXIJA O DOCUMENTO FISCAL", fill=(60, 60, 65, 195), font=_font("mono", 12))
    side_l = side_img.rotate(90, expand=True)
    side_r = side_img.rotate(270, expand=True)
    slip.alpha_composite(side_l, dest=(4, 95))
    slip.alpha_composite(side_r, dest=(w - 26, 95))

    img.alpha_composite(slip, dest=(4, 4))
    angle = rng.uniform(-4.5, 4.5)
    out = img.rotate(angle, expand=True, resample=Image.Resampling.BICUBIC)
    out.info["transcript"] = [acquirer, f"REDE {acquirer.upper()} - Via Cliente", *[ln.strip() for ln in lines]]
    return out


def apply_scratches_and_scan_borders(
    image: Image.Image,
    rng: random.Random,
    add_pen_scratches: bool = True,
    add_scan_borders: bool = True,
    add_fold_or_streak: bool = True,
) -> Image.Image:
    """Adiciona riscos de caneta, linhas de scanner, dobra de papel e bordas escuras."""
    out = image.convert("RGBA")
    w, h = out.size
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    if add_pen_scratches:
        pen = rng.choice(_PEN_COLORS)
        n_marks = rng.randint(1, 3)
        for _ in range(n_marks):
            kind = rng.choice(["check", "underline", "scratch"])
            px = rng.randint(int(w * 0.12), int(w * 0.85))
            py = rng.randint(int(h * 0.25), int(h * 0.75))
            col = (*pen, rng.randint(165, 225))
            if kind == "check":
                draw.line(
                    [(px, py), (px + 10, py + 12), (px + 32, py - 14)],
                    fill=col,
                    width=rng.randint(2, 3),
                )
            elif kind == "underline":
                ulen = rng.randint(50, 140)
                draw.line(
                    [(px, py), (px + ulen, py + rng.randint(-3, 3))],
                    fill=col,
                    width=rng.randint(2, 3),
                )
            else:
                # Risco acidental de caneta
                pts = [
                    (px, py),
                    (px + rng.randint(-60, 80), py + rng.randint(-30, 45)),
                    (px + rng.randint(-40, 110), py + rng.randint(-20, 60)),
                ]
                draw.line(pts, fill=col, width=rng.randint(2, 3))

    if add_fold_or_streak and rng.random() < 0.65:
        # Linha horizontal de dobra no meio ou risco vertical fino de scanner
        if rng.random() < 0.5:
            fy = int(h * rng.uniform(0.46, 0.54))
            draw.line([(0, fy), (w, fy + rng.randint(-4, 4))], fill=(150, 150, 150, 75), width=2)
            draw.line([(0, fy + 2), (w, fy + 2 + rng.randint(-4, 4))], fill=(255, 255, 255, 95), width=1)
        else:
            sx = rng.randint(int(w * 0.08), int(w * 0.92))
            draw.line([(sx, 0), (sx, h)], fill=(70, 70, 70, 65), width=1)

    if add_scan_borders:
        # Bordas escuras irregulares de scanner (como em 6436820.pdf e 6324935.pdf)
        sides = rng.sample(["top", "bottom", "left", "right"], k=rng.randint(1, 3))
        b_col = (20, 20, 22, 230)
        for s in sides:
            thick = rng.randint(3, 12)
            if s == "top":
                draw.rectangle((0, 0, w, thick), fill=b_col)
            elif s == "bottom":
                draw.rectangle((0, h - thick, w, h), fill=b_col)
            elif s == "left":
                draw.rectangle((0, 0, thick, h), fill=b_col)
            elif s == "right":
                draw.rectangle((w - thick, 0, w, h), fill=b_col)

    out.alpha_composite(overlay)
    return out.convert("RGB")


def compose_document_artifacts(
    image: Image.Image,
    field_values: dict,
    page_size_mm: dict,
    rng: random.Random,
    preset: str = None,
    context: dict = None,
    label: dict = None,
) -> tuple[Image.Image, list[dict]]:
    """Aplica carimbos, assinaturas, comprovantes POS e riscos sobre a página 1
    e retorna `(image_rgb, special_objects_mm)`.

    `context` (ver `augmentation/context.py`) diz quem é o emitente, data, valor
    (None = sem comprovante POS), `field_id` do CNPJ e se há canhoto; sem ele
    cai na adivinhação de chaves de `field_values` (compatibilidade).
    `label` permite posicionar artefatos na área livre abaixo do conteúdo.
    """
    canvas = image.convert("RGBA")
    w_px, h_px = canvas.size
    w_mm = page_size_mm.get("w", 210.0)
    h_mm = page_size_mm.get("h", 297.0)
    sx = w_px / w_mm
    sy = h_px / h_mm

    def _px_to_bbox_mm(x0, y0, bw, bh):
        x0_c = max(0, min(w_px, x0))
        y0_c = max(0, min(h_px, y0))
        x1_c = max(0, min(w_px, x0 + bw))
        y1_c = max(0, min(h_px, y0 + bh))
        return {
            "x": round(x0_c / sx, 3),
            "y": round(y0_c / sy, 3),
            "w": round(max(0.1, (x1_c - x0_c) / sx), 3),
            "h": round(max(0.1, (y1_c - y0_c) / sy), 3),
            "unit": "mm",
        }

    from augmentation.context import guess_context

    ctx = context or guess_context(field_values)
    emit_cnpj, emit_nome, emit_end = ctx["cnpj"], ctx["name"], ctx["address"]
    date_br, valor_nf, has_receipt = ctx["date_br"], ctx["amount"], ctx["has_receipt"]

    # Área livre abaixo do último texto (em px): onde carimbos "cabem" sem
    # cobrir o documento. None quando o conteúdo ocupa a folha (ex.: DANFE).
    _els = [e for e in (label or {}).get("elements", []) if e.get("page", 1) == 1 and "bbox" in e]
    bottom_mm = max((e["bbox"]["y"] + e["bbox"]["h"] for e in _els), default=None)

    def _free_band(obj_h):
        if bottom_mm is None:
            return None
        top, low = (bottom_mm + 3.0) * sy, h_px - obj_h - 8
        return (top, low) if low - top > 4 else None

    if preset is None:
        # Sorteio do combo de artefatos físicos para o dataset geral
        presets = ["none", "stamps_only", "stamp_and_cnpj", "pos_overlay", "signature_and_scratches"]
        weights = [0.20, 0.30, 0.20, 0.15, 0.15]
        if valor_nf is None:  # sem valor monetário (ex.: CC-e): sem comprovante POS
            weights[3] = 0.0
        preset = rng.choices(presets, weights=weights, k=1)[0]
    if valor_nf is None and preset in ("pos_overlay", "pos_and_stamp"):
        preset = "stamps_only"

    special_objs = []

    if preset in ("stamps_only", "stamp_and_cnpj", "all_stamps", "pos_and_stamp"):
        st_img = render_receipt_stamp(rng, emit_nome, date_br=date_br)
        st_text = st_img.info.get("transcript", [])
        target_w = int(w_px * rng.uniform(0.22, 0.28))
        target_h = int(st_img.height * (target_w / st_img.width))
        st_img = st_img.resize((target_w, target_h), Image.Resampling.BICUBIC)
        # Posiciona no quadro Reservado ao Fisco (inferior direito) ou espaço de produtos
        band = _free_band(target_h)
        if band is not None and rng.random() < 0.85:
            px = int(w_px * rng.uniform(0.10, 0.62))
            py = int(rng.uniform(*band))
        elif rng.random() < 0.55:
            px = int(w_px * rng.uniform(0.62, 0.70))
            py = int(h_px * rng.uniform(0.82, 0.87))
        else:
            px = int(w_px * rng.uniform(0.18, 0.55))
            py = int(h_px * rng.uniform(0.55, 0.72))
        px = min(px, w_px - target_w - 6)
        py = min(py, h_px - target_h - 6)
        canvas.alpha_composite(st_img, dest=(px, py))
        special_objs.append(
            {
                "type": "stamp",
                "subtype": "receipt_stamp",
                "page": 1,
                "bbox": _px_to_bbox_mm(px, py, target_w, target_h),
                "field_id": None,
                "text": st_text,
            }
        )

    if preset in ("stamp_and_cnpj", "cnpj_stamp", "all_stamps"):
        c_img = render_cnpj_stamp(rng, emit_cnpj, emit_nome, emit_end)
        c_text = c_img.info.get("transcript", [])
        target_w = int(w_px * rng.uniform(0.24, 0.30))
        target_h = int(c_img.height * (target_w / c_img.width))
        c_img = c_img.resize((target_w, target_h), Image.Resampling.BICUBIC)
        band = _free_band(target_h)
        px = min(int(w_px * rng.uniform(0.56, 0.68)), w_px - target_w - 8)
        py = min(int(h_px * rng.uniform(0.60, 0.72)), h_px - target_h - 8)
        if band is not None and rng.random() < 0.85:
            py = int(rng.uniform(*band))
        canvas.alpha_composite(c_img, dest=(px, py))
        special_objs.append(
            {
                "type": "stamp",
                "subtype": "cnpj_stamp",
                "page": 1,
                "bbox": _px_to_bbox_mm(px, py, target_w, target_h),
                "field_id": ctx["cnpj_field_id"],
                "text": c_text,
            }
        )

    if preset in ("pos_overlay", "pos_and_stamp"):
        pos_img = render_pos_receipt(rng, emit_cnpj, emit_nome, emit_end, date_br, valor_nf)
        pos_text = pos_img.info.get("transcript", [])
        target_w = int(w_px * rng.uniform(0.23, 0.27))
        target_h = int(pos_img.height * (target_w / pos_img.width))
        pos_img = pos_img.resize((target_w, target_h), Image.Resampling.BICUBIC)
        band = _free_band(target_h)
        px = min(int(w_px * rng.uniform(0.60, 0.68)), w_px - target_w - 10)
        py = min(int(h_px * rng.uniform(0.55, 0.63)), h_px - target_h - 10)
        if band is not None and rng.random() < 0.85:
            py = int(rng.uniform(*band))
        canvas.alpha_composite(pos_img, dest=(px, py))
        special_objs.append(
            {
                "type": "pos_receipt",
                "page": 1,
                "bbox": _px_to_bbox_mm(px, py, target_w, target_h),
                "field_id": None,
                "text": pos_text,
            }
        )

    if preset in ("signature_and_scratches", "stamps_only", "pos_overlay") and rng.random() < 0.7:
        sig_img = render_signature_layer(rng, width_px=220, height_px=75)
        target_w = int(w_px * rng.uniform(0.14, 0.20))
        target_h = int(sig_img.height * (target_w / sig_img.width))
        sig_img = sig_img.resize((target_w, target_h), Image.Resampling.BICUBIC)
        if has_receipt:  # canhoto superior (DANFE/DACTE)
            px = int(w_px * rng.uniform(0.28, 0.52))
            py = int(h_px * rng.uniform(0.035, 0.055))
        else:  # rubrica no fim do conteúdo (sem canhoto, o topo é o cabeçalho)
            band = _free_band(target_h)
            px = int(w_px * rng.uniform(0.50, 0.75))
            py = int(rng.uniform(*band)) if band is not None else int(h_px * rng.uniform(0.80, 0.90))
        canvas.alpha_composite(sig_img, dest=(px, py))
        special_objs.append(
            {
                "type": "signature",
                "page": 1,
                "bbox": _px_to_bbox_mm(px, py, target_w, target_h),
                "field_id": None,
            }
        )

    rgb = canvas.convert("RGB")
    if preset != "none":
        rgb = apply_scratches_and_scan_borders(
            rgb,
            rng,
            add_pen_scratches=(preset == "signature_and_scratches" or rng.random() < 0.35),
            add_scan_borders=(rng.random() < 0.6),
            add_fold_or_streak=(rng.random() < 0.5),
        )
    return rgb, special_objs
