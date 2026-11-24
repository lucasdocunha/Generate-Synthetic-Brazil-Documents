"""Tipos comuns do HTML por documento."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass
class HtmlResult:
    html_full: str  # HTML autocontido (CSS inline)
    pdf_bytes: bytes  # PDF do Chromium (usado quando image_source="html")
    n_pages: int
    style: dict = field(default_factory=dict)  # estilo sorteado (vai para o metadata)
    md_style: str = "table"  # formato do Markdown alvo: table | bullets


@dataclass
class HtmlSpec:
    """`render(xml, field_values, seed, renderer, lib_pdf=None, need_pdf=True) -> HtmlResult`.

    `lib_pdf`: PDF real (renderers/) já gerado — as specs derivadas de PDF partem dele;
    `need_pdf`: False evita o render Chromium quando a imagem vem do PDF real."""

    name: str
    render: Callable
