"""Renderizador da Consulta Web do Portal da Nota Fiscal Eletrônica.

Suporta os dois layouts reais observados nos documentos da Câmara dos Deputados:
- `classic_fazenda`: layout clássico do Portal Nacional (`consultaImpressao.aspx`,
  ref. PDF 6324935 pág. 2) com caixas estilo formulário e linhas pontilhadas;
- `modern_svrs`: layout moderno em cards (ref. PDF 7438757 págs. 1-3) com logo
  `NFe Nota Fiscal Eletrônica`, pílulas de status, detalhamento de itens e
  botão `Voltar`.
"""

import xml.etree.ElementTree as ET

from .danfe.danfe_conf import URL
from .utils import format_cep, format_cpf_cnpj, format_number, format_phone, get_date_utc, get_tag_text
from .xfpdf import xFPDF


def _t(node, tag: str) -> str:
    return get_tag_text(node, URL, tag) if node is not None else ""


def _format_portal_key(key: str) -> str:
    if len(key) != 44:
        return key
    cnpj_fmt = format_cpf_cnpj(key[6:20])
    n_fmt = f"{key[25:28]}.{key[28:31]}.{key[31:34]}"
    c_fmt = f"{key[34:37]}.{key[37:40]}.{key[40:43]}"
    return f"{key[0:2]}-{key[2:6]}-{cnpj_fmt}-{key[20:22]}-{key[22:25]}-{n_fmt}-{c_fmt}-{key[43]}"


class PortalNfe(xFPDF):
    def __init__(self, xml: str, variant: str = "modern_svrs"):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.variant = variant
        self.set_margins(left=10, top=10, right=10)
        self.set_auto_page_break(auto=True, margin=12)
        self.set_title("Portal da Nota Fiscal Eletronica")

        root = ET.fromstring(xml)
        self.inf_nfe = root.find(f"{URL}infNFe")
        self.prot_nfe = root.find(f"{URL}protNFe")
        self.ide = root.find(f"{URL}ide")
        self.emit = root.find(f"{URL}emit")
        self.dest = root.find(f"{URL}dest")
        self.totais = root.find(f"{URL}total")
        self.transp = root.find(f"{URL}transp")
        self.cobr = root.find(f"{URL}cobr")
        self.pag = root.find(f"{URL}pag")
        self.det = root.findall(f"{URL}det")
        self.inf_adic = root.find(f"{URL}infAdic")

        self.key_nfe = (self.inf_nfe.attrib.get("Id", "") if self.inf_nfe is not None else "")[3:]

        if self.variant == "classic_fazenda":
            self._render_classic()
        else:
            self._render_modern()

    def _extract_common(self):
        dt_emi, hr_emi = get_date_utc(_t(self.ide, "dhEmi"))
        emit_doc = _t(self.emit, "CNPJ") or _t(self.emit, "CPF")
        dest_doc = _t(self.dest, "CNPJ") or _t(self.dest, "CPF")
        prot = _t(self.prot_nfe, "nProt") or "353220054921351"
        dh_prot = _t(self.prot_nfe, "dhRecbto") or _t(self.ide, "dhEmi")
        dt_p, hr_p = get_date_utc(dh_prot)
        dig_val = _t(self.prot_nfe, "digVal") or "Bc2T+kG3gS25YXOhsi65f2cgg3Y="
        return {
            "dt_emi": dt_emi,
            "hr_emi": hr_emi,
            "dh_emi_full": f"{dt_emi} {hr_emi}-03:00",
            "n_nf": _t(self.ide, "nNF"),
            "serie": _t(self.ide, "serie"),
            "nat_op": _t(self.ide, "natOp"),
            "v_nf": format_number(_t(self.totais, "vNF"), 2),
            "v_prod": format_number(_t(self.totais, "vProd"), 2),
            "v_bc": format_number(_t(self.totais, "vBC"), 2),
            "v_icms": format_number(_t(self.totais, "vICMS"), 2),
            "v_bcst": format_number(_t(self.totais, "vBCST"), 2),
            "v_st": format_number(_t(self.totais, "vST"), 2),
            "v_frete": format_number(_t(self.totais, "vFrete"), 2),
            "v_seg": format_number(_t(self.totais, "vSeg"), 2),
            "v_desc": format_number(_t(self.totais, "vDesc"), 2),
            "v_outro": format_number(_t(self.totais, "vOutro"), 2),
            "v_ipi": format_number(_t(self.totais, "vIPI"), 2),
            "v_pis": format_number(_t(self.totais, "vPIS"), 2),
            "v_cofins": format_number(_t(self.totais, "vCOFINS"), 2),
            "emit_doc_fmt": format_cpf_cnpj(emit_doc),
            "emit_nome": _t(self.emit, "xNome"),
            "emit_fant": _t(self.emit, "xFant") or _t(self.emit, "xNome"),
            "emit_ie": _t(self.emit, "IE"),
            "emit_uf": _t(self.emit, "UF"),
            "emit_mun": f"{_t(self.emit, 'cMun')} - {_t(self.emit, 'xMun')}",
            "emit_end": f"{_t(self.emit, 'xLgr')}, {_t(self.emit, 'nro')}",
            "emit_bairro": _t(self.emit, "xBairro"),
            "emit_cep": format_cep(_t(self.emit, "CEP")),
            "emit_fone": format_phone(_t(self.emit, "fone")),
            "dest_doc_fmt": format_cpf_cnpj(dest_doc),
            "dest_is_cnpj": len(dest_doc) > 11,
            "dest_nome": _t(self.dest, "xNome"),
            "dest_ie": _t(self.dest, "IE"),
            "dest_uf": _t(self.dest, "UF"),
            "dest_mun": f"{_t(self.dest, 'cMun')} - {_t(self.dest, 'xMun')}",
            "dest_end": f"{_t(self.dest, 'xLgr')}, {_t(self.dest, 'nro')}",
            "dest_bairro": _t(self.dest, "xBairro"),
            "dest_cep": format_cep(_t(self.dest, "CEP")),
            "dest_fone": format_phone(_t(self.dest, "fone")),
            "prot": prot,
            "dh_prot_full": f"{dt_p} às {hr_p}-03:00",
            "dig_val": dig_val,
        }

    # ------------------------------------------------------------------
    # Variante 1: Classic Fazenda (6324935.pdf pág. 2)
    # ------------------------------------------------------------------
    def _classic_section_title(self, title: str, centered: bool = False):
        self.ln(2)
        self.set_font("Helvetica", "B", 9.5)
        self.set_text_color(80, 75, 70)
        self.cell(0, 5, title, align="C" if centered else "L", new_x="LMARGIN", new_y="NEXT")
        y = self.get_y()
        self.set_draw_color(210, 180, 140)
        self.set_dash_pattern(dash=0.6, gap=0.6)
        self.line(self.l_margin, y, self.w - self.r_margin, y)
        self.set_dash_pattern(dash=0, gap=0)
        self.set_draw_color(160, 160, 160)
        self.set_text_color(0, 0, 0)
        self.ln(1.5)

    def _classic_field_row(self, cols):
        """cols: list of (width_mm, label, value)."""
        x0 = self.l_margin + 1.5
        y0 = self.get_y()
        # Labels
        self.set_font("Helvetica", "", 7)
        self.set_text_color(60, 60, 60)
        cx = x0
        for w, label, _ in cols:
            self.set_xy(cx, y0)
            self.cell(w - 1.5, 4, label, align="L")
            cx += w
        # Value input boxes
        y_box = y0 + 4.2
        self.set_font("Helvetica", "", 7.5)
        self.set_text_color(0, 0, 0)
        cx = x0
        for w, _, val in cols:
            self.set_fill_color(255, 255, 255)
            self.set_draw_color(180, 180, 180)
            self.rect(cx, y_box, w - 2.0, 5.2, style="DF")
            self.set_xy(cx + 1, y_box + 0.8)
            self.cell(w - 4.0, 3.8, str(val or "")[:62], align="L")
            cx += w
        self.set_y(y_box + 6.4)

    def _classic_card(self, rows):
        y_start = self.get_y()
        h_est = len(rows) * 10.6 + 2.5
        self.set_fill_color(246, 246, 246)
        self.set_draw_color(170, 170, 170)
        self.rect(self.l_margin, y_start, self.epw, h_est, style="DF")
        self.set_y(y_start + 1.5)
        for r in rows:
            self._classic_field_row(r)
        self.set_y(y_start + h_est + 1.5)

    def _render_classic(self):
        d = self._extract_common()
        self.add_page()
        # Browser header
        self.set_font("Helvetica", "", 7)
        self.cell(60, 4, d["dt_emi"], align="L")
        self.cell(70, 4, "Portal da Nota Fiscal Eletrônica", align="C")
        self.cell(0, 4, "", new_x="LMARGIN", new_y="NEXT")
        self.ln(4)

        # Chave de acesso box
        self._classic_card(
            [
                [
                    (105, "Chave de Acesso", _format_portal_key(self.key_nfe)),
                    (42, "Número NF-e", d["n_nf"]),
                    (40, "Versão", "4.00"),
                ]
            ]
        )

        self._classic_section_title("Dados da NF-e", centered=True)
        self._classic_card(
            [
                [
                    (18, "Modelo", "55"),
                    (18, "Série", d["serie"]),
                    (26, "Número", d["n_nf"]),
                    (42, "Data de Emissão", d["dh_emi_full"]),
                    (45, "Data/Hora de Saída ou da Entrada", d["dh_emi_full"]),
                    (38, "Valor Total da Nota Fiscal", d["v_nf"]),
                ]
            ]
        )

        self._classic_section_title("Emitente")
        self._classic_card(
            [
                [
                    (42, "CNPJ", d["emit_doc_fmt"]),
                    (88, "Nome / Razão Social", d["emit_nome"]),
                    (38, "Inscrição Estadual", d["emit_ie"]),
                    (19, "UF", d["emit_uf"]),
                ]
            ]
        )

        self._classic_section_title("Destinatário")
        self._classic_card(
            [
                [
                    (42, "CNPJ" if d["dest_is_cnpj"] else "CPF", d["dest_doc_fmt"]),
                    (88, "Nome / Razão Social", d["dest_nome"]),
                    (38, "Inscrição Estadual", d["dest_ie"]),
                    (19, "UF", d["dest_uf"]),
                ],
                [
                    (62, "Destino da operação", "1 - Operação Interna"),
                    (62, "Consumidor final", "1 - Consumidor final"),
                    (63, "Presença do Comprador", "1 - Operação presencial"),
                ],
            ]
        )

        self._classic_section_title("Emissão")
        self._classic_card(
            [
                [
                    (62, "Processo", "0 - com aplicativo do Contribuinte"),
                    (42, "Versão do Processo", "4.0.0"),
                    (42, "Tipo de Emissão", "1 - Normal"),
                    (41, "Finalidade", "1 - Normal"),
                ],
                [
                    (62, "Natureza da Operação", d["nat_op"]),
                    (32, "Tipo da Operação", "1 - Saída"),
                    (36, "Forma de Pagamento", "0 - À vista"),
                    (57, "Digest Value da NF-e", d["dig_val"]),
                ],
            ]
        )

        self._classic_section_title(
            "Situação Atual: AUTORIZADA (Ambiente de autorização: homologação)"
        )
        self._classic_card(
            [
                [
                    (52, "Eventos da NF-e", "Autorização de Uso"),
                    (46, "Protocolo", d["prot"]),
                    (46, "Data Autorização", d["dh_prot_full"]),
                    (43, "Data Inclusão AN", d["dh_prot_full"]),
                ]
            ]
        )

        # Browser footer
        self.set_y(-12)
        self.set_font("Helvetica", "", 6.5)
        self.set_text_color(50, 50, 50)
        self.cell(
            150,
            4,
            "http://www.nfe.fazenda.gov.invalid/portal/consultaImpressao.aspx?tipoConsulta=resumo",
            align="L",
        )
        self.cell(0, 4, "1/1", align="R")

    # ------------------------------------------------------------------
    # Variante 2: Modern SVRS Cards (7438757.pdf págs. 1-3)
    # ------------------------------------------------------------------
    def _modern_logo_header(self):
        d = self._extract_common()
        y0 = self.get_y()
        # Ícone decorativo verde + NFe
        self.set_fill_color(46, 160, 90)
        self.rect(11, y0 + 1.5, 3.2, 7.2, style="F")
        self.set_fill_color(28, 92, 148)
        self.rect(13.2, y0 + 3.0, 1.5, 5.7, style="F")
        self.set_line_width(0.2)
        self.set_font("Helvetica", "B", 18)
        self.set_text_color(28, 92, 148)
        self.set_xy(16, y0 + 1)
        self.cell(16, 8, "NFe")
        self.set_font("Helvetica", "", 9)
        self.set_text_color(80, 130, 170)
        self.set_xy(32, y0 + 1.5)
        self.cell(35, 4, "Nota Fiscal")
        self.set_xy(32, y0 + 5.2)
        self.cell(35, 4, "Eletrônica")

        # Chave + Versão
        self.set_y(y0 + 13)
        self.set_text_color(30, 30, 30)
        self.set_font("Helvetica", "B", 7)
        self.cell(150, 4, "Chave de acesso", align="L")
        self.cell(0, 4, "Versão XML", align="L", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 7.5)
        self.cell(150, 4, _format_portal_key(self.key_nfe), align="L")
        self.cell(0, 4, "4.00", align="L", new_x="LMARGIN", new_y="NEXT")
        self.ln(2)
        self.set_draw_color(220, 220, 220)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(2)
        return d

    def _modern_card(self, title: str, rows: list):
        if self.get_y() + len(rows) * 9 + 14 > self.h - 15:
            self.add_page()
        y0 = self.get_y()
        h_card = len(rows) * 8.5 + 10.5
        self.set_draw_color(218, 218, 218)
        self.set_fill_color(255, 255, 255)
        self.rect(self.l_margin, y0, self.epw, h_card, style="DF")
        self.set_xy(self.l_margin + 3, y0 + 2)
        self.set_font("Helvetica", "", 9.5)
        self.set_text_color(55, 55, 55)
        self.cell(self.epw - 6, 5, title, new_x="LMARGIN", new_y="NEXT")
        y_line = self.get_y() + 0.5
        self.line(self.l_margin + 3, y_line, self.w - self.r_margin - 3, y_line)
        self.set_y(y_line + 1.5)

        for row in rows:
            y_r = self.get_y()
            cx = self.l_margin + 3
            for w, lbl, val in row:
                self.set_xy(cx, y_r)
                self.set_font("Helvetica", "B", 6.8)
                self.set_text_color(25, 25, 25)
                self.cell(w, 3.5, str(lbl), align="L")
                self.set_xy(cx, y_r + 3.6)
                self.set_font("Helvetica", "", 7)
                self.set_text_color(45, 45, 45)
                self.cell(w, 3.8, str(val or "")[:68], align="L")
                cx += w
            self.set_y(y_r + 8.5)
        self.set_y(y0 + h_card + 2.5)

    def _render_modern(self):
        self.add_page()
        d = self._modern_logo_header()

        self.set_font("Helvetica", "", 9.5)
        self.set_text_color(50, 50, 50)
        self.cell(0, 5, "NF-e", new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

        self._modern_card(
            "Dados da NF-e",
            [[(90, "Número NF-e", d["n_nf"]), (90, "Data de Emissão", d["dh_emi_full"])]],
        )
        self._modern_card(
            "Dados Básicos",
            [
                [
                    (25, "Modelo", "55"),
                    (25, "Série", d["serie"]),
                    (32, "Número", d["n_nf"]),
                    (45, "Data de Emissão", d["dh_emi_full"]),
                    (30, "Data Saída/Entrada", d["dt_emi"]),
                    (27, "Valor Total da Nota", d["v_nf"]),
                ]
            ],
        )
        self._modern_card(
            "Emitente",
            [
                [
                    (42, "CNPJ", d["emit_doc_fmt"]),
                    (85, "Nome / Razão Social", d["emit_nome"]),
                    (38, "Inscrição Estadual", d["emit_ie"]),
                    (19, "UF", d["emit_uf"]),
                ]
            ],
        )
        self._modern_card(
            "Destinatário",
            [
                [
                    (42, "CNPJ" if d["dest_is_cnpj"] else "CPF", d["dest_doc_fmt"]),
                    (85, "Nome / Razão Social", d["dest_nome"]),
                    (38, "Inscrição Estadual", d["dest_ie"]),
                    (19, "UF", d["dest_uf"]),
                ],
                [
                    (60, "Destino da operação", "1 - Operação Interna"),
                    (60, "Consumidor final", "1 - Sim"),
                    (60, "Presença do Comprador", "1 - Operação presencial"),
                ],
            ],
        )
        self._modern_card(
            "Emissão",
            [
                [
                    (65, "Processo", "0 - Emissão de NF-e com aplicativo do Contribuinte"),
                    (38, "Versão do Processo", "4.01"),
                    (40, "Tipo Emissão", "1 - Normal"),
                    (40, "Finalidade", "1 - NF-e normal"),
                ],
                [
                    (65, "Natureza da Operação", d["nat_op"]),
                    (38, "Tipo da Operação", "1 - Saída"),
                    (40, "Forma de Pagamento", "0 - À vista"),
                    (40, "Digest Value da NF-e", d["dig_val"][:24]),
                ],
            ],
        )
        self._modern_card(
            "Situação  [AUTORIZADA]    Ambiente  [HOMOLOGAÇÃO]",
            [
                [
                    (65, "Eventos da NF-e", "Autorizado o uso da NF-e"),
                    (60, "Protocolo", d["prot"]),
                    (55, "Data / Hora", d["dh_prot_full"]),
                ]
            ],
        )
        self._modern_card(
            "Dados do Emitente",
            [
                [(92, "Nome / Razão Social", d["emit_nome"]), (92, "Nome Fantasia", d["emit_fant"])],
                [(92, "CNPJ", d["emit_doc_fmt"]), (92, "Endereço", d["emit_end"])],
                [(92, "Bairro / Distrito", d["emit_bairro"]), (92, "CEP", d["emit_cep"])],
                [(92, "Município", d["emit_mun"]), (92, "Telefone", d["emit_fone"])],
                [(92, "UF", d["emit_uf"]), (92, "Inscrição Estadual", d["emit_ie"])],
            ],
        )
        self._modern_card(
            "Dados do Destinatário / Remetente",
            [
                [
                    (92, "Nome / Razão Social", d["dest_nome"]),
                    (92, "CNPJ / CPF", d["dest_doc_fmt"]),
                ],
                [(92, "Endereço", d["dest_end"]), (92, "Bairro / Distrito", d["dest_bairro"])],
                [(92, "CEP", d["dest_cep"]), (92, "Município", d["dest_mun"])],
                [(92, "Telefone", d["dest_fone"]), (92, "UF", d["dest_uf"])],
            ],
        )

        # Produtos e Serviços
        item_rows = []
        for idx, det_el in enumerate(self.det, start=1):
            prod = det_el.find(f"{URL}prod")
            c_prod = _t(prod, "cProd")
            x_prod = _t(prod, "xProd")
            ncm = _t(prod, "NCM")
            cfop = _t(prod, "CFOP")
            u_com = _t(prod, "uCom")
            q_com = format_number(_t(prod, "qCom"), 4)
            v_un = format_number(_t(prod, "vUnCom"), 4)
            v_prod = format_number(_t(prod, "vProd"), 2)
            item_rows.append(
                [
                    (22, f"Item {idx} - Cód.", c_prod),
                    (66, "Descrição", x_prod),
                    (22, "NCM", ncm),
                    (16, "CFOP", cfop),
                    (14, "Unid.", u_com),
                    (22, "Qtd.", q_com),
                    (22, "Valor(R$)", v_prod),
                ]
            )
            item_rows.append(
                [
                    (45, "Valor Unitário Comercial", v_un),
                    (45, "Código EAN Comercial", "SEM GTIN"),
                    (45, "Unidade Tributável", u_com),
                    (45, "Quantidade Tributável", q_com),
                ]
            )
        if item_rows:
            self._modern_card("Dados dos Produtos e Serviços", item_rows)

        self._modern_card(
            "Totais — Imposto Sobre Circulação de Mercadorias e Serviços (ICMS)",
            [
                [
                    (46, "Base de Cálculo ICMS", d["v_bc"]),
                    (46, "Valor do ICMS", d["v_icms"]),
                    (46, "Base de Cálculo ICMS ST", d["v_bcst"]),
                    (46, "Valor ICMS Substituição", d["v_st"]),
                ],
                [
                    (46, "Valor Total dos Produtos", d["v_prod"]),
                    (46, "Valor do Frete", d["v_frete"]),
                    (46, "Valor do Seguro", d["v_seg"]),
                    (46, "Outras Despesas", d["v_outro"]),
                ],
                [
                    (46, "Valor Total do IPI", d["v_ipi"]),
                    (46, "Valor Total da NFe", d["v_nf"]),
                    (46, "Valor Total dos Descontos", d["v_desc"]),
                    (46, "Valor do PIS / COFINS", f"{d['v_pis']} / {d['v_cofins']}"),
                ],
            ],
        )

        obs = _t(self.inf_adic, "infCpl")
        if obs:
            self._modern_card("Informações Adicionais", [[(184, "Descrição", obs[:110])]])

        # Botão Voltar (estilo 7438757.pdf pág. 3)
        y_btn = self.get_y() + 2
        if y_btn < self.h - 20:
            self.set_draw_color(70, 140, 200)
            self.rect(self.w / 2 - 10, y_btn, 20, 6.5)
            self.set_xy(self.w / 2 - 10, y_btn + 1.2)
            self.set_font("Helvetica", "", 7.5)
            self.set_text_color(70, 140, 200)
            self.cell(20, 4, "Voltar", align="C")
            self.set_text_color(0, 0, 0)
