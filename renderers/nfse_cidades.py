"""Layouts de NFS-e no estilo de diferentes prefeituras (dado sintético).

Cada layout reproduz a *organização* típica de um modelo municipal (cabeçalho,
ordem e forma dos blocos, tipografia), sem brasões nem marcas reais: o brasão
é um círculo vazio. Os dados vêm do envelope Ginfes; número da nota e código de
verificação são derivados do RPS (simulados, determinísticos).
"""

from __future__ import annotations

import hashlib

from .utils import format_cpf_cnpj, format_number

CITY_LAYOUTS = {
    # capitais (estrutura de blocos e rótulos extraída de notas reais do corpus; sem brasões)
    "sao_paulo": "São Paulo: brasão, caixa número/data/código, Prestador, Tomador, Intermediário, Discriminação, retenções e Outras Informações",
    "porto_velho": "Porto Velho: modelo nacional com Prestador/Tomador completos, código do serviço, discriminação e retenções federais",
    "fortaleza": "Fortaleza: grade de identificação (RPS, competência, substituída), dados do tomador, detalhamento de valores e cálculo do ISSQN",
    "maceio": "Maceió: cabeçalho com Secretaria de Economia, prestador/tomador em linhas, código/atividade e quadro de valores",
    "rio_branco": "Rio Branco: Secretaria de Finanças, campos rótulo: valor, discriminação/dados adicionais e valores",
    # estilos genéricos (inventados, não são de uma cidade específica)
    "generico_faixa": "Faixa de título escura, prestador e tomador lado a lado, campos em linha",
    "generico_tabela": "Tabela com coluna de rótulo sombreada à esquerda",
    "generico_grade": "Faixa de cabeçalho em cinza escuro, grade completa e valores em tabela",
    "generico_pontilhado": "Cabeçalho com filete duplo e campos pontilhados",
    "generico_colunas": "Duas colunas (prestador | tomador) e quadro de valores em destaque",
}


def simulated_ids(numero_rps: str, dt: str, doc: str) -> tuple[str, str]:
    """Número da nota (ano/seq) e código de verificação — simulados e determinísticos."""
    h = hashlib.sha256(f"{numero_rps}|{dt}|{doc}".encode()).hexdigest().upper()
    return f"{dt[:4]}/{int(numero_rps):06d}", f"{h[:4]}-{h[4:8]}-{h[8:12]}"


class _P:
    """Atalhos de desenho sobre o FPDF."""

    def __init__(self, pdf):
        self.p = pdf

    def text(self, x, y, w, h, txt, size=8, style="", align="L", font="Helvetica", color=(0, 0, 0)):
        p = self.p
        p.set_xy(x, y)
        p.set_font(font, style, size)
        p.set_text_color(*color)
        p.multi_cell(w, h, txt, border=0, align=align)
        p.set_text_color(0, 0, 0)

    def box(self, x, y, w, h, fill=None, lw=0.2):
        p = self.p
        p.set_line_width(lw)
        if fill:
            p.set_fill_color(*fill)
            p.rect(x, y, w, h, style="DF")
        else:
            p.rect(x, y, w, h)
        p.set_line_width(0.2)

    def field(self, x, y, w, h, label, value, bold=False, font="Helvetica", fill=None):
        self.box(x, y, w, h, fill)
        self.text(x + 1.5, y + 0.8, w - 3, 3, label.upper(), 5.5, "B", font=font)
        self.text(x + 1.5, y + 4.2, w - 3, 3.6, value, 8, "B" if bold else "", font=font)


def render_city(pdf, layout: str, d: dict):
    """`d`: dict com os textos já formatados (ver NfseLegado._data). Capitais com molde
    (nfse_cidades_specs/*.json, extraído de notas reais) usam `render_spec`."""
    from .nfse_spec import has_spec, render_spec

    if has_spec(layout):
        return render_spec(pdf, layout, d)
    getattr(_Layouts, layout)(_P(pdf), d)


class _Layouts:
    @staticmethod
    def generico_faixa(g: _P, d):
        f = "Times"
        g.box(10, 10, 190, 12, (40, 40, 60))
        g.text(10, 12.5, 190, 6, f"PREFEITURA DA CIDADE DE {d['mun'].upper()}", 12, "B", "C", f, (255, 255, 255))
        g.text(10, 24, 190, 5, "NOTA FISCAL DE SERVIÇOS ELETRÔNICA", 10, "B", "C", f)
        g.text(10, 30, 95, 4, f"Nota nº {d['nota']}", 9, "B", "L", f)
        g.text(105, 30, 95, 4, f"Emitida em {d['data']}    Código de verificação: {d['cod']}", 9, "", "R", f)
        y = 40
        for x, title, rows in ((10, "PRESTADOR", [("Razão social", d["prest"]), ("CNPJ", d["prest_doc"]), ("Inscrição municipal", d["im"]),
                                                  ("Município", d["mun"])]),
                               (105, "TOMADOR", [("Nome / razão social", d["tom"]), ("CPF/CNPJ", d["tom_doc"]), ("Endereço", d["end"]),
                                                  ("Município", d["mun"])])):
            g.text(x, y, 90, 4, title, 9, "B", "L", f)
            g.p.line(x, y + 4.5, x + 90, y + 4.5)
            yy = y + 6
            for lab, val in rows:
                g.text(x, yy, 32, 4, lab + ":", 8, "B", "L", f)
                g.text(x + 32, yy, 58, 4, val, 8, "", "L", f)
                yy += 8 if len(val) < 30 else 12
        y = 88
        g.text(10, y, 190, 4, "DISCRIMINAÇÃO DOS SERVIÇOS", 9, "B", "L", f); g.p.line(10, y + 4.5, 200, y + 4.5)
        g.text(10, y + 7, 190, 4, f"Item da lista de serviços: {d['item']}", 8, "", "L", f)
        g.text(10, y + 14, 190, 4, d["disc"], 9, "", "L", f)
        y = 140
        g.box(10, y, 190, 5, (225, 225, 235)); g.text(12, y + 1, 186, 3.5, "VALORES", 8, "B", "L", f)
        for i, (lab, val, b) in enumerate((("Valor dos serviços (R$)", d["valor"], 0), ("Alíquota (%)", d["aliq"], 0),
                                            ("Valor do ISS (R$)", d["iss"], 1), ("Simples Nacional", d["simples"], 0))):
            g.text(12, y + 8 + i * 6, 60, 4, lab + ":", 9, "B", "L", f)
            g.text(75, y + 8 + i * 6, 60, 4, val, 9, "B" if b else "", "L", f)

    @staticmethod
    def generico_tabela(g: _P, d):
        g.text(10, 10, 190, 5, f"PREFEITURA DE {d['mun'].upper()} - SECRETARIA MUNICIPAL DE FINANÇAS", 9, "B", "C")
        g.text(10, 16, 190, 5, "NOTA FISCAL DE SERVIÇOS ELETRÔNICA - NFS-e", 11, "B", "C")
        rows = [("Número da nota", d["nota"]), ("Data e hora de emissão", d["data"]), ("Código de verificação", d["cod"]),
                ("Prestador - razão social", d["prest"]), ("Prestador - CNPJ", d["prest_doc"]), ("Prestador - inscrição municipal", d["im"]),
                ("Tomador - nome / razão social", d["tom"]), ("Tomador - CPF/CNPJ", d["tom_doc"]), ("Tomador - endereço", d["end"]),
                ("Código do serviço", d["item"]), ("Discriminação do serviço", d["disc"]), ("Valor dos serviços (R$)", d["valor"]),
                ("Alíquota (%)", d["aliq"]), ("Valor do ISS (R$)", d["iss"]), ("Optante pelo Simples Nacional", d["simples"])]
        y = 26
        for lab, val in rows:
            h = 24 if lab.startswith("Discrimin") else 9
            g.box(10, y, 60, h, (232, 232, 232)); g.box(70, y, 130, h)
            g.text(12, y + 1.5, 56, 3.5, lab, 7, "B"); g.text(72, y + 1.5, 126, 3.6, val, 8)
            y += h

    @staticmethod
    def generico_grade(g: _P, d):
        g.box(10, 10, 190, 16, (60, 60, 60))
        g.text(14, 12, 130, 5, f"PREFEITURA MUNICIPAL DE {d['mun'].upper()}", 11, "B", color=(255, 255, 255))
        g.text(14, 18.5, 130, 5, "NOTA FISCAL ELETRÔNICA DE SERVIÇOS", 8, "", color=(255, 255, 255))
        g.text(145, 12, 52, 4, f"NFS-e {d['nota']}", 10, "B", "R", color=(255, 255, 255))
        g.text(145, 18.5, 52, 4, f"Emissão {d['data']}", 8, "", "R", color=(255, 255, 255))
        y = 30
        g.field(10, y, 95, 11, "Código de verificação", d["cod"], True); g.field(105, y, 95, 11, "Optante pelo Simples Nacional", d["simples"])
        y += 14
        for title, cols in (("Prestador", [("Razão social", d["prest"], 110), ("CNPJ", d["prest_doc"], 80)]),
                            ("Tomador", [("Nome / razão social", d["tom"], 110), ("CPF/CNPJ", d["tom_doc"], 80)])):
            g.text(10, y, 190, 4, title.upper(), 8, "B"); y += 4.5
            x = 10
            for lab, val, w in cols:
                g.field(x, y, w, 11, lab, val); x += w
            y += 11
            g.field(10, y, 190, 11, "Endereço / inscrição municipal", d["end"] if title == "Tomador" else f"IM {d['im']} - {d['mun']}")
            y += 15
        g.text(10, y, 190, 4, "DISCRIMINAÇÃO DOS SERVIÇOS", 8, "B"); y += 4.5
        g.box(10, y, 190, 26); g.text(12, y + 2, 186, 3.6, d["disc"], 8); y += 30
        heads = ["Código", "Valor dos serviços (R$)", "Alíquota (%)", "ISS (R$)"]
        vals = [d["item"], d["valor"], d["aliq"], d["iss"]]
        for i, (hh, v) in enumerate(zip(heads, vals)):
            g.box(10 + i * 47.5, y, 47.5, 6, (210, 210, 210)); g.box(10 + i * 47.5, y + 6, 47.5, 8)
            g.text(11.5 + i * 47.5, y + 1.3, 44, 3.5, hh, 7, "B"); g.text(11.5 + i * 47.5, y + 8.2, 44, 4, v, 9, "B" if i == 3 else "")

    @staticmethod
    def generico_pontilhado(g: _P, d):
        g.text(10, 10, 190, 5, f"PREFEITURA MUNICIPAL DE {d['mun'].upper()}", 12, "B", "C")
        g.text(10, 16, 190, 5, "NOTA FISCAL DE SERVIÇOS ELETRÔNICA", 10, "", "C")
        g.p.line(10, 23, 200, 23); g.p.line(10, 24, 200, 24)
        g.text(10, 27, 190, 4, f"Nº {d['nota']}      Data: {d['data']}      Cód. verificação: {d['cod']}", 9, "B", "C")

        def dotted(y, lab, val):
            g.text(10, y, 70, 4, lab, 8, "B")
            g.text(60, y, 140, 4, " " + val, 8)
            g.p.set_dash_pattern(dash=0.3, gap=0.8); g.p.line(10, y + 5, 200, y + 5); g.p.set_dash_pattern(dash=0, gap=0)
        y = 36
        g.text(10, y, 190, 4, "PRESTADOR", 9, "B"); y += 6
        for lab, val in (("Razão social", d["prest"]), ("CNPJ", d["prest_doc"]), ("Inscrição municipal", d["im"])):
            dotted(y, lab, val); y += 7
        y += 4; g.text(10, y, 190, 4, "TOMADOR", 9, "B"); y += 6
        for lab, val in (("Nome / razão social", d["tom"]), ("CPF/CNPJ", d["tom_doc"]), ("Endereço", d["end"])):
            dotted(y, lab, val); y += 7
        y += 4; g.text(10, y, 190, 4, "SERVIÇO", 9, "B"); y += 6
        dotted(y, "Item da lista", d["item"]); y += 8
        g.text(10, y, 190, 3.6, d["disc"], 8); y += 26
        g.box(10, y, 190, 5); g.text(12, y + 1, 186, 3.5, "VALORES", 8, "B"); y += 5
        for i, (lab, val) in enumerate((("Serviços (R$)", d["valor"]), ("Alíquota (%)", d["aliq"]), ("ISS (R$)", d["iss"]), ("Simples", d["simples"]))):
            g.field(10 + i * 47.5, y, 47.5, 11, lab, val, i == 2)

    @staticmethod
    def generico_colunas(g: _P, d):
        g.box(10, 10, 190, 20, (240, 240, 240))
        g.text(14, 12, 124, 4, f"PREFEITURA MUNICIPAL DE {d['mun'].upper()}", 9, "B")
        g.text(14, 19, 120, 5, "NOTA FISCAL DE SERVIÇOS ELETRÔNICA", 9, "")
        g.text(140, 12, 58, 4, f"Nº {d['nota']}", 11, "B", "R"); g.text(140, 19, 58, 4, d["data"], 8, "", "R")
        g.text(140, 24, 58, 4, f"Verificação {d['cod']}", 8, "", "R")
        y = 34
        g.box(10, y, 93, 5, (225, 225, 225)); g.box(107, y, 93, 5, (225, 225, 225))
        g.text(12, y + 1, 90, 3.5, "PRESTADOR", 7, "B"); g.text(109, y + 1, 90, 3.5, "TOMADOR", 7, "B"); y += 5
        for (l1, v1), (l2, v2) in zip((("Razão social", d["prest"]), ("CNPJ", d["prest_doc"]), ("Inscrição municipal", d["im"]), ("Município", d["mun"])),
                                      (("Nome / razão social", d["tom"]), ("CPF/CNPJ", d["tom_doc"]), ("Endereço", d["end"]), ("Município", d["mun"]))):
            g.field(10, y, 93, 11, l1, v1); g.field(107, y, 93, 11, l2, v2); y += 11
        y += 4
        g.box(10, y, 190, 5, (225, 225, 225)); g.text(12, y + 1, 186, 3.5, f"DISCRIMINAÇÃO DOS SERVIÇOS - item {d['item']}", 7, "B"); y += 5
        g.box(10, y, 190, 30); g.text(12, y + 2, 186, 3.6, d["disc"], 8); y += 34
        g.box(10, y, 190, 26, (248, 248, 248))
        g.text(14, y + 3, 90, 4, "Valor dos serviços (R$)", 8, "B"); g.text(104, y + 3, 90, 4, d["valor"], 10, "B", "R")
        g.text(14, y + 10, 90, 4, f"Alíquota {d['aliq']}%  -  Valor do ISS (R$)", 8, "B"); g.text(104, y + 10, 90, 4, d["iss"], 10, "B", "R")
        g.text(14, y + 17, 90, 4, "Optante pelo Simples Nacional", 8, "B"); g.text(104, y + 17, 90, 4, d["simples"], 9, "", "R")


def _sections(g: _P, y, sections, font="Helvetica", title="bar"):
    """sections: [(titulo, [[(rótulo, valor, largura), ...], ...])]; largura em mm (soma 190)."""
    for t, rows in sections:
        if t:
            if title == "bar":
                g.box(10, y, 190, 5, (225, 225, 225)); g.text(12, y + 1, 186, 3.5, t.upper(), 7, "B", font=font)
            else:
                g.text(10, y, 190, 4, t, 8, "B", font=font); g.p.line(10, y + 4.6, 200, y + 4.6)
            y += 5.5
        for row in rows:
            x = 10
            h = 9.5
            for lab, val, w in row:
                g.field(x, y, w, h, lab, val, font=font); x += w
            y += h
        y += 2
    return y


def _common(d):
    """Campos extras sintéticos/derivados usados pelas capitais."""
    comp = d["data"][3:]
    return {"comp": comp, "uf": d["end"].rsplit(" - ", 1)[-1][:2], "zero": "0,00", "nada": "-"}


def _sao_paulo(g: _P, d):
    c = _common(d)
    g.box(10, 10, 28, 28)
    g.text(40, 12, 100, 4, f"PREFEITURA DO MUNICÍPIO DE {d['mun'].upper()}", 9, "B", "C")
    g.text(40, 18, 100, 4, "SECRETARIA MUNICIPAL DE FINANÇAS", 7, "", "C")
    g.text(40, 25, 100, 4, "NOTA FISCAL DE SERVIÇOS ELETRÔNICA - NFS-e", 9, "B", "C")
    g.field(145, 10, 55, 9, "Número da Nota", d["nota"], True)
    g.field(145, 19, 55, 9, "Data e Hora de Emissão", d["data"])
    g.field(145, 28, 55, 9, "Código de Verificação", d["cod"], True)
    y = _sections(g, 42, [
        ("Prestador de Serviços", [[("CPF/CNPJ:", d["prest_doc"], 95), ("Inscrição Municipal:", d["im"], 95)],
                                   [("Nome/Razão Social:", d["prest"], 140), ("UF:", c["uf"], 50)], [("Município:", d["mun"], 190)]]),
        ("Tomador de Serviços", [[("Nome/Razão Social:", d["tom"], 130), ("CPF/CNPJ:", d["tom_doc"], 60)],
                                 [("Inscrição Municipal:", c["nada"], 60), ("Endereço:", d["end"], 130)]]),
        ("Intermediário de Serviços", [[("CPF/CNPJ:", c["nada"], 60), ("Nome/Razão Social:", c["nada"], 130)]]),
    ])
    g.box(10, y, 190, 5, (225, 225, 225)); g.text(12, y + 1, 186, 3.5, "DISCRIMINAÇÃO DOS SERVIÇOS", 7, "B"); y += 5
    g.box(10, y, 190, 26); g.text(12, y + 2, 186, 3.6, d["disc"], 8); y += 28
    g.field(10, y, 190, 9.5, "Valor total do serviço (R$)", d["valor"], True); y += 11.5
    ret = [("INSS (R$)", c["zero"]), ("IRRF (R$)", c["zero"]), ("CSLL (R$)", c["zero"]), ("COFINS (R$)", c["zero"]), ("PIS/PASEP (R$)", c["zero"])]
    for i, (l, v) in enumerate(ret):
        g.field(10 + i * 38, y, 38, 9.5, l, v)
    y += 11.5
    y = _sections(g, y, [("", [[("Valor Total das Deduções (R$)", c["zero"], 38), ("Base de Cálculo (R$)", d["valor"], 38),
                                ("Alíquota (%)", d["aliq"], 38), ("Valor do ISS (R$)", d["iss"], 38), ("Crédito (R$)", c["zero"], 38)],
                               [("Município da Prestação do Serviço", d["mun"], 95), ("Número Inscrição da Obra", c["nada"], 47), ("Valor Aproximado dos Tributos", c["zero"], 48)]])])
    g.box(10, y, 190, 5, (225, 225, 225)); g.text(12, y + 1, 186, 3.5, "OUTRAS INFORMAÇÕES", 7, "B")
    g.box(10, y + 5, 190, 14); g.text(12, y + 7, 186, 3.4, f"Item da lista de serviços: {d['item']}. Optante pelo Simples Nacional: {d['simples']}.", 7)


def _porto_velho(g: _P, d):
    c = _common(d)
    g.box(10, 10, 190, 22)
    g.text(40, 12, 120, 5, f"Prefeitura do Município de {d['mun']}", 11, "B", "C")
    g.text(40, 18, 120, 4, "Secretaria Municipal de Fazenda - SEMFAZ", 9, "", "C")
    g.text(40, 24, 120, 5, "NOTA FISCAL DE SERVIÇOS ELETRÔNICA - NFS-e", 9, "B", "C")
    g.text(165, 12, 34, 4, f"Número\n{d['nota']}", 8, "B", "C")
    y = _sections(g, 34, [
        ("", [[("Data/Hora da Emissão", d["data"], 50), ("Competência", c["comp"], 40), ("Código de verificação", d["cod"], 50),
               ("Município de Prestação do Serviço", d["mun"], 50)],
              [("Regime de Tributação", "Normal", 95), ("Exigibilidade do ISSQN", "Exigível", 95)]]),
        ("Prestador dos Serviços", [[("Nome/Razão Social", d["prest"], 130), ("CNPJ", d["prest_doc"], 60)],
                                    [("Endereço", d["end"] if False else d["mun"], 100), ("Número:", c["nada"], 30), ("Complemento", c["nada"], 60)],
                                    [("Bairro", c["nada"], 60), ("Cidade", d["mun"], 70), ("UF", c["uf"], 20), ("CEP", c["nada"], 40)],
                                    [("Inscrição Municipal", d["im"], 60), ("Email", c["nada"], 130)]]),
        ("Tomador de Serviços/Destinatário", [[("Nome/Razão Social", d["tom"], 130), ("CNPJ/CPF", d["tom_doc"], 60)],
                                              [("Endereço", d["end"], 130), ("Número:", c["nada"], 20), ("Complemento", c["nada"], 40)],
                                              [("Bairro", c["nada"], 60), ("Cidade", d["mun"], 60), ("UF", c["uf"], 20), ("CEP", c["nada"], 30), ("País", "Brasil", 20)]]),
        ("Código do Serviço", [[("Item da lista", d["item"], 190)]]),
    ], title="line")
    g.text(10, y, 190, 4, "DISCRIMINAÇÃO DOS SERVIÇOS", 8, "B"); g.p.line(10, y + 4.6, 200, y + 4.6)
    g.box(10, y + 6, 190, 24); g.text(12, y + 8, 186, 3.6, d["disc"], 8); y += 33
    y = _sections(g, y, [("Retenções Federais", [[("PIS", c["zero"], 38), ("COFINS", c["zero"], 38), ("INSS", c["zero"], 38), ("IR", c["zero"], 38), ("CSLL", c["zero"], 38)],
                                                   [("Valor dos serviços (R$)", d["valor"], 63), ("Alíquota (%)", d["aliq"], 63), ("Valor do ISS (R$)", d["iss"], 64)]])], title="line")


def _fortaleza(g: _P, d):
    c = _common(d)
    g.box(10, 10, 24, 22)
    g.text(36, 11, 120, 4, f"PREFEITURA MUNICIPAL DE {d['mun'].upper()}", 9, "B", "C")
    g.text(36, 16, 120, 4, "SECRETARIA MUNICIPAL DAS FINANÇAS", 8, "", "C")
    g.text(36, 22, 120, 4, "NOTA FISCAL ELETRÔNICA DE SERVIÇO - NFS-e", 8, "B", "C")
    g.field(160, 10, 40, 22, "Número da NFS-e", d["nota"], True)
    y = _sections(g, 34, [
        ("", [[("Data e Hora da Emissão", d["data"], 50), ("Número do RPS", c["nada"], 35), ("Competência", c["comp"], 35), ("No. NFS-e substituída", c["nada"], 35),
               ("Código de Verificação", d["cod"], 35)], [("Local da Prestação", f"{d['mun']} - {c['uf']}", 95), ("Natureza Operação", "1-Tributação no Município", 95)]]),
        ("Dados do Prestador de Serviços", [[("Razão Social/Nome", d["prest"], 100), ("CPF/CNPJ", d["prest_doc"], 50), ("Insc Municipal", d["im"], 40)],
                                            [("Endereço e CEP", d["mun"], 100), ("Município", d["mun"], 50), ("Telefone", c["nada"], 40)]]),
        ("Dados do Tomador de Serviços", [[("Razão Social/Nome", d["tom"], 100), ("Nome Fantasia", c["nada"], 50), ("CPF/CNPJ", d["tom_doc"], 40)],
                                          [("Endereço e CEP", d["end"], 100), ("Complemento", c["nada"], 30), ("Município", d["mun"], 30), ("Telefone", c["nada"], 30)]]),
    ])
    g.box(10, y, 190, 5, (225, 225, 225)); g.text(12, y + 1, 186, 3.5, "DISCRIMINAÇÃO DOS SERVIÇOS", 7, "B"); y += 5
    g.box(10, y, 190, 26); g.text(12, y + 2, 186, 3.6, f"{d['item']} - {d['disc']}", 8); y += 28
    y = _sections(g, y, [
        ("Detalhamento de Valores - Prestador dos Serviços", [[("(-) Desconto Incondicionado", c["zero"], 38), ("PIS(R$)", c["zero"], 38), ("COFINS(R$)", c["zero"], 38),
                                                              ("IR(R$)", c["zero"], 38), ("CSLL(R$)", c["zero"], 38)],
                                                             [("Outras Retenções", c["zero"], 47), ("(-) ISS Retido", c["zero"], 47), ("(=) Valor Líquido R$", d["valor"], 48), ("Opção Simples Nacional", d["simples"], 48)]]),
        ("Cálculo do ISSQN devido no Município", [[("Base de cálculo R$", d["valor"], 63), ("(X) Alíquota %", d["aliq"], 63), ("(=) Valor do ISS R$", d["iss"], 64)]]),
    ])
    g.box(10, y, 190, 5, (225, 225, 225)); g.text(12, y + 1, 186, 3.5, "AVISOS", 7, "B")


def _maceio(g: _P, d):
    c = _common(d)
    g.box(10, 10, 22, 22)
    g.text(34, 11, 110, 4, f"PREFEITURA MUNICIPAL DE {d['mun'].upper()}", 9, "B", "C")
    g.text(34, 16, 110, 4, "SECRETARIA MUNICIPAL DE ECONOMIA", 8, "", "C")
    g.text(34, 22, 110, 4, "NOTA FISCAL ELETRÔNICA DE SERVIÇO - NFS-e", 8, "B", "C")
    g.field(146, 10, 54, 11, "Nº NFS-e:", d["nota"], True); g.field(146, 21, 54, 11, "Data e Hora de Emissão", d["data"])
    y = _sections(g, 34, [
        ("", [[("Cod Verificação NFS-e", d["cod"], 50), ("Competencia:", c["comp"], 40), ("Número do RPS", c["nada"], 35), ("NFS-e Substituída", c["nada"], 30),
               ("Código Verificação RPS", c["nada"], 35)]]),
        ("Dados do Prestador de Serviço", [[("Razão Social/Nome:", d["prest"], 130), ("CNPJ/CPF:", d["prest_doc"], 60)],
                                           [("Endereço:", d["mun"], 100), ("Município:", d["mun"], 40), ("UF:", c["uf"], 20), ("Tel:", c["nada"], 30)]]),
        ("Dados do Tomador de Serviço", [[("Razão Social/Nome:", d["tom"], 130), ("CNPJ/CPF:", d["tom_doc"], 60)],
                                         [("Endereço:", d["end"], 130), ("CCM:", c["nada"], 60)]]),
        ("Código do Serviço / Atividade", [[("", f"{d['item']} - {d['disc'][:60]}", 190)]]),
    ])
    g.box(10, y, 190, 5, (225, 225, 225)); g.text(12, y + 1, 186, 3.5, "DISCRIMINAÇÃO DOS SERVIÇOS", 7, "B"); y += 5
    g.box(10, y, 190, 26); g.text(12, y + 2, 186, 3.6, d["disc"], 8); y += 28
    _sections(g, y, [("", [[("Natureza Operação", "1-Exigível", 47), ("Local da Prestação", f"{d['mun'].upper()} - {c['uf']}", 47), ("ISSQN a Reter", "( ) Sim (X) Não", 48), ("Opção Simples Nacional", d["simples"], 48)],
                           [("Valor das Deduções (R$)", c["zero"], 38), ("Outras Retenções (R$)", c["zero"], 38), ("Descontos Incondicionados (R$)", c["zero"], 38),
                            ("Descontos Condicionados (R$)", c["zero"], 38), ("Retenções Federais (R$)", c["zero"], 38)],
                           [("Valor Líquido (R$)", d["valor"], 47), ("Base de Cálculo (R$)", d["valor"], 47), ("Alíquota", d["aliq"], 48), ("Valor do ISSQN (R$)", d["iss"], 48)]])])


def _rio_branco(g: _P, d):
    c = _common(d)
    f = "Helvetica"
    g.box(10, 10, 190, 20)
    g.text(14, 12, 120, 4, "Secretaria Municipal de Finanças", 8, "B")
    g.text(14, 17, 150, 5, f"Prefeitura do Município de {d['mun']}", 11, "B")
    g.text(14, 24, 150, 4, f"CEP: 69.900-901 - {d['mun']}/AC", 7)
    g.text(165, 12, 34, 4, f"NFS-e n°: {d['nota']}", 8, "B", "R"); g.text(165, 18, 34, 4, f"Emitida em: {d['data']}", 8, "", "R")
    y = 33
    for title, rows in (("Dados do Prestador de Serviço", [("Razão Social:", d["prest"]), ("Nome Fantasia:", c["nada"]), ("CNPJ:", d["prest_doc"]),
                                                            ("Inscrição Municipal:", d["im"]), ("Endereço:", d["mun"]), ("Cidade:", d["mun"])]),
                        ("Dados do Tomador de Serviços", [("Nome/Razão Social:", d["tom"]), ("CPF/CNPJ:", d["tom_doc"]), ("Insc. Municipal:", c["nada"]),
                                                          ("Endereço:", d["end"]), ("Cidade:", d["mun"]), ("E-mail:", c["nada"])])):
        g.box(10, y, 190, 5, (225, 225, 225)); g.text(12, y + 1, 186, 3.5, title, 7, "B"); y += 5
        for i in range(0, len(rows), 2):
            for j, (lab, val) in enumerate(rows[i:i + 2]):
                x = 10 + j * 95
                g.box(x, y, 95, 8); g.text(x + 1.5, y + 2, 28, 3.5, lab, 7, "B"); g.text(x + 30, y + 2, 63, 3.5, val, 7.5)
            y += 8
        y += 3
    g.box(10, y, 190, 5, (225, 225, 225)); g.text(12, y + 1, 186, 3.5, "Discriminação do Serviço/Dados Adicionais", 7, "B"); y += 5
    g.box(10, y, 190, 30); g.text(12, y + 2, 186, 3.6, d["disc"], 8); y += 32
    for i, (lab, val) in enumerate((("Serviço:", f"{d['item']}"), ("Local de Prestação", f"{d['mun'].upper()} - AC"), ("Valor do Serviço(R$)", d["valor"]), ("Alíquota (%)", d["aliq"]), ("Valor do ISS (R$)", d["iss"]))):
        g.field(10 + i * 38, y, 38, 10, lab, val)
    y += 12
    g.box(10, y, 190, 9); g.text(12, y + 2, 186, 3.5, f"Natureza Operação: Tributação no município - Código Verificação: {d['cod']} - Optante Simples: {d['simples']}", 7)


for _n, _f in (("sao_paulo", _sao_paulo), ("porto_velho", _porto_velho), ("fortaleza", _fortaleza), ("maceio", _maceio), ("rio_branco", _rio_branco)):
    setattr(_Layouts, _n, staticmethod(_f))
