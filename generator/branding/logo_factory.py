"""Geração procedural de logotipos corporativos e de ERPs (PLANO_GERADOR.md §5.3).

Sintetiza imagens PNG em memória (`BytesIO`) via Pillow em 4 famílias visuais
inspiradas nos documentos reais da Câmara dos Deputados:
1. `badge_seal`: selo circular/hexagonal escuro com anel duplo e monograma
   (ex.: "Amor em Grãos Café", 6324935.pdf);
2. `modern_corporate`: ícone geométrico colorido + wordmark em duas linhas
   (ex.: "IMPAKTA SOLUÇÕES", 7438757.pdf);
3. `fuel_shield`: escudo/faixas horizontais típico de postos e transportadoras;
4. `minimal_monogram`: caixa arredondada + iniciais e nome comercial.
"""

from io import BytesIO
from pathlib import Path
import random
import re

from PIL import Image, ImageDraw, ImageFont

_FONT_CANDIDATES = {
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
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
    ],
}

_PALETTES = [
    ((22, 62, 115), (230, 126, 34), (255, 255, 255)),   # Azul marinho + Laranja
    ((28, 28, 30), (200, 160, 90), (255, 255, 255)),    # Preto + Dourado café (6324935)
    ((0, 102, 153), (46, 184, 114), (255, 255, 255)),   # Azul + Verde (7438757 Impakta)
    ((155, 28, 31), (241, 196, 15), (255, 255, 255)),   # Vermelho + Amarelo (Postos)
    ((44, 62, 80), (52, 152, 219), (255, 255, 255)),    # Grafite + Azul claro
    ((18, 90, 50), (243, 156, 18), (255, 255, 255)),    # Verde escuro + Âmbar
    ((35, 35, 35), (120, 120, 120), (255, 255, 255)),   # Monocromático P&B
]

_STOPWORDS = {
    "DE", "DA", "DO", "DAS", "DOS", "E", "COMERCIO", "COMÉRCIO", "INDUSTRIA",
    "INDÚSTRIA", "DISTRIBUIDORA", "ATACADO", "SERVICOS", "SERVIÇOS",
    "COMERCIAL", "LTDA", "ME", "EIRELI", "SA", "S.A.", "EPP", "MEI",
}


def load_font(style: str, size: int):
    for p in _FONT_CANDIDATES.get(style, []):
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, size=size)
            except OSError:
                pass
    return ImageFont.load_default(size=size)


def _extract_brand_tokens(company_name: str):
    words = [re.sub(r"[^A-Za-zÀ-ÿ0-9]", "", w).upper() for w in company_name.split()]
    words = [w for w in words if w]
    core = [w for w in words if w not in _STOPWORDS] or words or ["BR"]
    brand_main = core[0][:12]
    brand_sub = (core[1] if len(core) > 1 else (words[0] if words else "SOLUÇÕES"))[:16]
    initials = "".join(w[0] for w in core[:3])[:3] or brand_main[:2]
    return brand_main, brand_sub, initials


def generate_company_logo(rng: random.Random, company_name: str, style: str = None) -> BytesIO:
    styles = ("badge_seal", "modern_corporate", "fuel_shield", "minimal_monogram")
    style = style or rng.choice(styles)
    primary, accent, light = rng.choice(_PALETTES)
    main_txt, sub_txt, initials = _extract_brand_tokens(company_name)

    w, h = 360, 220
    img = Image.new("RGBA", (w, h), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)

    if style == "badge_seal":
        cx, cy, r = w // 2, h // 2, 92
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=primary)
        draw.ellipse((cx - r + 7, cy - r + 7, cx + r - 7, cy + r - 7), outline=accent, width=3)
        draw.ellipse((cx - r + 13, cy - r + 13, cx + r - 13, cy + r - 13), outline=light, width=1)
        # Estrela/grão decorativo no topo
        draw.polygon([(cx, cy - 58), (cx - 10, cy - 38), (cx, cy - 44), (cx + 10, cy - 38)], fill=accent)
        f_main = load_font("serif_bold", 30)
        f_sub = load_font("sans", 15)
        draw.text((cx, cy - 2), main_txt[:10], fill=light, font=f_main, anchor="mm")
        draw.line((cx - 52, cy + 20, cx + 52, cy + 20), fill=accent, width=2)
        draw.text((cx, cy + 38), sub_txt[:12], fill=accent, font=f_sub, anchor="mm")

    elif style == "modern_corporate":
        # Barras inclinadas/geométricas no topo + nome forte embaixo (estilo Impakta)
        bx = 45
        for i, col in enumerate((primary, accent, primary, (100, 180, 220))):
            x0 = bx + i * 24
            draw.polygon([(x0 + 12, 24), (x0 + 28, 24), (x0 + 16, 78), (x0, 78)], fill=col)
        draw.arc((bx + 95, 20, bx + 165, 85), start=200, end=45, fill=accent, width=8)
        f_main = load_font("sans_bold", 42)
        f_sub = load_font("sans", 18)
        draw.text((w // 2, 125), main_txt, fill=primary, font=f_main, anchor="mm")
        spaced = " ".join(sub_txt[:10])
        draw.text((w // 2, 168), spaced, fill=(90, 90, 90), font=f_sub, anchor="mm")
        draw.line((40, 192, w - 40, 192), fill=accent, width=4)

    elif style == "fuel_shield":
        # Escudo com faixas laterais (típico de Auto Posto / Transportes)
        pts = [(40, 30), (w - 40, 30), (w - 20, 110), (w // 2, 195), (20, 110)]
        draw.polygon(pts, fill=primary, outline=accent)
        draw.rectangle((35, 78, w - 35, 132), fill=accent)
        f_init = load_font("sans_bold", 34)
        f_sub = load_font("sans_bold", 22)
        draw.text((w // 2, 54), initials, fill=light, font=f_init, anchor="mm")
        draw.text((w // 2, 105), main_txt[:10], fill=primary, font=f_sub, anchor="mm")
        draw.text((w // 2, 152), sub_txt[:10], fill=light, font=load_font("sans", 16), anchor="mm")

    else:  # minimal_monogram
        draw.rounded_rectangle((18, 45, 138, 175), radius=22, fill=primary, outline=accent, width=4)
        f_init = load_font("sans_bold", 48)
        draw.text((78, 110), initials[:2], fill=light, font=f_init, anchor="mm")
        f_main = load_font("sans_bold", 30)
        f_sub = load_font("sans", 18)
        draw.text((155, 92), main_txt[:9], fill=primary, font=f_main, anchor="lm")
        draw.line((155, 118, w - 20, 118), fill=accent, width=3)
        draw.text((155, 142), sub_txt[:12], fill=(80, 80, 80), font=f_sub, anchor="lm")

    buf = BytesIO()
    # Fundo branco sólido evita artefatos de canal alfa em PDFs antigos
    rgb = Image.new("RGB", (w, h), (255, 255, 255))
    rgb.paste(img, mask=img.split()[3])
    rgb.save(buf, format="PNG")
    buf.seek(0)
    return buf
