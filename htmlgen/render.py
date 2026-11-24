"""HTML -> PDF (Chromium headless, paginação A4 real via CSS @page) -> PNG."""

from __future__ import annotations

import os
from pathlib import Path

from playwright.sync_api import sync_playwright

import atexit

import fitz

from rasterization.raster import rasterize


class HtmlRenderer:
    """Mantém um Chromium aberto (lançar um browser por amostra seria o
    gargalo do lote). Use como context manager, um por processo/worker."""

    def __enter__(self):
        self._pw = sync_playwright().start()
        self._browser = self._launch()
        self._page = self._browser.new_page()
        return self

    def _launch(self):
        """Usa o Chromium do Playwright; se a versão instalada do pacote não
        bater com os browsers da máquina, cai para HTMLGEN_CHROMIUM ou para o
        Chromium pré-instalado em /opt/pw-browsers/chromium."""
        try:
            return self._pw.chromium.launch()
        except Exception:
            for cand in (os.environ.get("HTMLGEN_CHROMIUM"), "/opt/pw-browsers/chromium"):
                if cand and Path(cand).is_file():
                    return self._pw.chromium.launch(executable_path=cand, args=["--no-sandbox"])
            raise

    def __exit__(self, *exc):
        self._browser.close()
        self._pw.stop()

    def html_to_pdf(self, html: str) -> bytes:
        self._page.set_content(html, wait_until="load")
        return self._page.pdf(prefer_css_page_size=True, print_background=True)

    def html_to_images(self, html: str, dpi: int = 200):
        pdf = self.html_to_pdf(html)
        return pdf, rasterize(pdf, dpi=dpi)

    def measure_mm(self, html: str, page_w_mm: float, margin_mm: float) -> float:
        """Altura (mm) que o <article> ocupa no layout de impressão — usada
        para esticar a tabela de itens até o fim da página, como no DANFE real."""
        px_w = int((page_w_mm - 2 * margin_mm) * 96 / 25.4)
        self._page.set_viewport_size({"width": px_w, "height": 1200})
        self._page.emulate_media(media="print")
        self._page.set_content(html, wait_until="load")
        h_px = self._page.evaluate("document.querySelector('article').getBoundingClientRect().height")
        return h_px * 25.4 / 96


def n_pages(pdf: bytes) -> int:
    d = fitz.open(stream=pdf, filetype="pdf")
    n = len(d)
    d.close()
    return n


_RENDERER: HtmlRenderer | None = None


def get_renderer() -> HtmlRenderer:
    """Chromium único por processo (worker do joblib): lançar um browser por
    amostra seria o gargalo do lote. Fechado no encerramento do processo."""
    global _RENDERER
    if _RENDERER is None:
        _RENDERER = HtmlRenderer().__enter__()
        atexit.register(lambda: _RENDERER and _RENDERER.__exit__(None, None, None))
    return _RENDERER
