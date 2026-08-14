"""PDF -> imagem (PLANO_GERADOR.md secao 4.1): PyMuPDF, sem dependência de
binário externo (Poppler), DPI/zoom controlável — a variação de DPI é a
forma mais simples de atender "diferentes resoluções" (secao Realismo).
"""

import fitz
from PIL import Image


def rasterize(pdf_path_or_bytes, dpi: int = 200):
    """Retorna lista de imagens PIL, uma por página, renderizadas no DPI dado."""
    if isinstance(pdf_path_or_bytes, (bytes, bytearray)):
        doc = fitz.open(stream=bytes(pdf_path_or_bytes), filetype="pdf")
    else:
        doc = fitz.open(pdf_path_or_bytes)

    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)
    images = []
    for page in doc:
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        images.append(img)
    doc.close()
    return images
