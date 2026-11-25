"""Renderizador PDF da NFS-e no padrão municipal legado (Ginfes v03, envelope de
lote de RPS), a partir do XML.

Não existe PDF oficial deste leiaute na lib BrazilFiscalReport: o visual é um
leiaute de referência em fpdf2 (cabeçalho da prefeitura com o número do RPS,
blocos de prestador, tomador, discriminação e valores). Os textos saem no
formato municipal típico (CPF/CNPJ com máscara, valores `1.234,56`), o que
permite casar cada campo do label com o seu bbox (`generator/labels/layout.py`).

O envelope Ginfes não traz razão social do prestador nem nome do município: esses
dois campos chegam por `razao_social_prestador` e `municipality_name` (kwargs).

Layouts por cidade: ver `nfse_cidades.py` (`city_layout`).
"""

import re
import xml.etree.ElementTree as ET

from .utils import format_cpf_cnpj, format_number
from .xfpdf import xFPDF

# O envelope mistura namespaces (ex.: ListaRps sem namespace): casa qualquer um
NS = "{*}"

_SIMPLES = {"1": "Sim", "2": "Não"}


def _t(node, tag: str) -> str:
    if node is None:
        return ""
    child = node.find(f"{NS}{tag}")
    return (child.text or "").strip() if child is not None else ""


def format_cep_nfse(cep) -> str:
    """CEP é xsd:integer no Ginfes (zero à esquerda se perde): reconstitui 8 dígitos."""
    digits = str(cep).strip().zfill(8)
    return f"{digits[:5]}-{digits[5:8]}"


def _br_date(iso: str) -> str:
    yyyy, mm, dd = iso[:10].split("-")
    return f"{dd}/{mm}/{yyyy}"


class NfseLegado(xFPDF):
    """Recebe o XML `EnviarLoteRpsEnvio` (Ginfes v03) como string."""

    def __init__(self, xml: str, razao_social_prestador: str = "", municipality_name: str = "", city_layout: str = "ginfes"):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.set_margins(left=10, top=10, right=10)
        self.set_auto_page_break(auto=False)
        self.set_title("NFS-e - padrao municipal legado (Ginfes)")
        self.razao_social_prestador = razao_social_prestador
        self.municipio = municipality_name

        root = ET.fromstring(xml)
        self.lote = root.find(f"{NS}LoteRps")
        self.rps = self.lote.find(f"{NS}ListaRps/{NS}Rps/{NS}InfRps")
        self.ident = self.rps.find(f"{NS}IdentificacaoRps")
        self.servico = self.rps.find(f"{NS}Servico")
        self.valores = self.servico.find(f"{NS}Valores")
        self.prestador = self.rps.find(f"{NS}Prestador")
        self.tomador = self.rps.find(f"{NS}Tomador")
        self.endereco = self.tomador.find(f"{NS}Endereco")

        self.city_layout = city_layout
        self.add_page()
        if city_layout == "ginfes":
            self._render()
        else:
            self._render_city()

    def _data(self) -> dict:
        from .nfse_cidades import simulated_ids

        cpf = self.tomador.find(f"{NS}IdentificacaoTomador/{NS}CpfCnpj")
        doc_t = _t(cpf, "Cnpj") or _t(cpf, "Cpf")
        dt = _t(self.rps, "DataEmissao")
        nota, cod = simulated_ids(_t(self.ident, "Numero"), dt, _t(self.prestador, "Cnpj"))
        e = self.endereco
        v = self.valores
        return {
            "mun": self.municipio, "nota": nota, "cod": cod, "data": _br_date(dt),
            "prest": self.razao_social_prestador, "prest_doc": format_cpf_cnpj(_t(self.prestador, "Cnpj")),
            "im": _t(self.prestador, "InscricaoMunicipal"), "tom": _t(self.tomador, "RazaoSocial"),
            "tom_doc": format_cpf_cnpj(doc_t),
            "end": f"{_t(e, 'Endereco')}, {_t(e, 'Numero')} - {_t(e, 'Bairro')} - CEP {format_cep_nfse(_t(e, 'Cep'))} - {_t(e, 'Uf')}",
            "item": _t(self.servico, "ItemListaServico"), "disc": _t(self.servico, "Discriminacao"),
            "valor": format_number(_t(v, "ValorServicos"), 2), "aliq": format_number(_t(v, "Aliquota"), 2),
            "iss": format_number(_t(v, "ValorIss"), 2), "simples": _SIMPLES.get(_t(self.rps, "OptanteSimplesNacional"), ""),
            **self._extras(nota, dt, e),
        }

    def _extras(self, nota, dt, e) -> dict:
        """Campos que o XML Ginfes não traz, derivados de forma determinística."""
        import hashlib

        h = int(hashlib.sha256(nota.encode()).hexdigest(), 16)
        nome = re.sub(r"[^a-z]", "", self.razao_social_prestador.lower())[:12] or "contato"
        hh = f"{(h >> 8) % 24:02d}:{(h >> 16) % 60:02d}:{(h >> 24) % 60:02d}"
        return {
            "datahora": f"{_br_date(dt)} {dt[11:19] if len(dt) >= 19 and dt[11:19] != '00:00:00' else hh}",
            "comp": _br_date(dt)[3:], "nota_seq": str(int(_t(self.ident, "Numero"))),
            "street": f"{_t(e, 'Endereco')}, {_t(e, 'Numero')}", "numero": _t(e, "Numero"), "bairro": _t(e, "Bairro"),
            "uf": _t(e, "Uf"), "cep": format_cep_nfse(_t(e, "Cep")), "email": f"{nome}@{['gmail','hotmail','outlook'][h % 3]}.com",
            "fone": f"({11 + h % 80}) 9{(h >> 4) % 10000:04d}-{(h >> 12) % 10000:04d}",
        }

    def _render_city(self):
        from .nfse_cidades import render_city

        render_city(self, self.city_layout, self._data())

    # --- helpers de desenho -------------------------------------------------
    def _field(self, x, y, w, h, label, value, bold=False):
        self.rect(x, y, w, h)
        self.set_xy(x + 1.5, y + 0.8)
        self.set_font("Helvetica", "B", 5.5)
        self.cell(w - 3, 3, label.upper())
        self.set_xy(x + 1.5, y + 4.2)
        self.set_font("Helvetica", "B" if bold else "", 8)
        self.multi_cell(w - 3, 3.6, value, border=0)

    def _title(self, y, text):
        self.set_fill_color(225, 225, 225)
        self.rect(10, y, 190, 5, style="DF")
        self.set_xy(11, y + 0.8)
        self.set_font("Helvetica", "B", 7)
        self.cell(188, 3.5, text)

    # --- leiaute ------------------------------------------------------------
    def _render(self):
        mun = self.municipio
        numero_rps = _t(self.ident, "Numero")
        numero_lote = _t(self.lote, "NumeroLote")
        dt_emissao = _t(self.rps, "DataEmissao")

        # Cabeçalho: prefeitura (esq.) e identificação do RPS (dir.)
        self.rect(10, 10, 120, 30)
        self.set_xy(12, 12)
        self.set_font("Helvetica", "B", 9)
        self.cell(116, 4, f"PREFEITURA MUNICIPAL DE {mun.upper()}")
        self.set_xy(12, 18)
        self.set_font("Helvetica", "B", 8)
        self.cell(116, 4, "NOTA FISCAL DE SERVIÇOS ELETRÔNICA - NFS-e")
        self.set_xy(12, 24)
        self.set_font("Helvetica", "", 6.5)
        self.multi_cell(116, 3.2, "Padrão municipal legado (Ginfes v03) - envio de lote de RPS\n"
                                  "Recibo Provisório de Serviços convertido em NFS-e pela prefeitura")

        self._field(130, 10, 35, 15, "Nº RPS", numero_rps, bold=True)
        self._field(165, 10, 35, 15, "Lote", numero_lote)
        self._field(130, 25, 70, 15, "Data de emissão", _br_date(dt_emissao))

        # Prestador
        self._title(43, "PRESTADOR DE SERVIÇOS")
        self._field(10, 48, 130, 11, "Razão social", self.razao_social_prestador)
        self._field(140, 48, 60, 11, "CPF/CNPJ", format_cpf_cnpj(_t(self.prestador, "Cnpj")))
        self._field(10, 59, 60, 11, "Inscrição municipal", _t(self.prestador, "InscricaoMunicipal"))
        self._field(70, 59, 130, 11, "Município", mun)

        # Tomador
        self._title(71, "TOMADOR DE SERVIÇOS")
        cpf_cnpj = self.tomador.find(f"{NS}IdentificacaoTomador/{NS}CpfCnpj")
        doc_tomador = _t(cpf_cnpj, "Cnpj") or _t(cpf_cnpj, "Cpf")
        self._field(10, 76, 130, 11, "Razão social / nome", _t(self.tomador, "RazaoSocial"))
        self._field(140, 76, 60, 11, "CPF/CNPJ", format_cpf_cnpj(doc_tomador))
        self._field(10, 87, 110, 11, "Endereço", _t(self.endereco, "Endereco"))
        self._field(120, 87, 25, 11, "Número", _t(self.endereco, "Numero"))
        self._field(145, 87, 55, 11, "Bairro", _t(self.endereco, "Bairro"))
        self._field(10, 98, 40, 11, "CEP", format_cep_nfse(_t(self.endereco, "Cep")))
        self._field(50, 98, 20, 11, "UF", _t(self.endereco, "Uf"))
        self._field(70, 98, 130, 11, "Município", mun)

        # Serviço
        self._title(110, "DISCRIMINAÇÃO DO SERVIÇO")
        self._field(10, 115, 50, 11, "Item da lista de serviço", _t(self.servico, "ItemListaServico"))
        self._field(60, 115, 140, 11, "Município da prestação", mun)
        self.rect(10, 126, 190, 22)
        self.set_xy(11.5, 127)
        self.set_font("Helvetica", "B", 5.5)
        self.cell(187, 3, "DISCRIMINAÇÃO")
        self.set_xy(11.5, 131)
        self.set_font("Helvetica", "", 8)
        self.multi_cell(187, 3.6, _t(self.servico, "Discriminacao"))

        # Valores
        self._title(150, "VALORES")
        base = _t(self.valores, "ValorServicos")
        iss = _t(self.valores, "ValorIss")
        self._field(10, 155, 47.5, 11, "Valor dos serviços (R$)", format_number(base, 2))
        self._field(57.5, 155, 47.5, 11, "Base de cálculo (R$)", format_number(base, 2))
        self._field(105, 155, 47.5, 11, "Alíquota (%)", format_number(_t(self.valores, "Aliquota"), 2))
        self._field(152.5, 155, 47.5, 11, "Valor do ISS (R$)", format_number(iss, 2), bold=True)
        self._field(10, 166, 95, 11, "ISS retido", "Não")
        self._field(105, 166, 95, 11, "Valor líquido (R$)", format_number(base, 2), bold=True)

        self._field(10, 177, 190, 11, "Optante pelo Simples Nacional",
                    _SIMPLES.get(_t(self.rps, "OptanteSimplesNacional"), ""))
