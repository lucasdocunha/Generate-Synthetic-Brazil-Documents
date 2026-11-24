"""XML da NF-e (nfeProc/NFe) -> modelo intermediário já formatado para
exibição (padrão brasileiro).

Esta é a ÚNICA camada que conhece o XML. Todo o resto (HTML, Markdown,
rótulos) consome o dict retornado por `parse_nfe`, então a fidelidade
"texto da imagem == texto do HTML == texto do Markdown" vem de todos
partirem exatamente das mesmas strings.

Funciona com qualquer XML de NF-e 4.00 (inclusive fixtures reais
anonimizadas): não depende de `field_values` do gerador.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

from lxml import etree

MOD_FRETE = {
    "0": "0 - Remetente",
    "1": "1 - Destinatário",
    "2": "2 - Terceiros",
    "3": "3 - Próprio/Rem",
    "4": "4 - Próprio/Dest",
    "9": "9 - Sem Frete",
}

TP_PAG = {
    "01": "Dinheiro", "02": "Cheque", "03": "Cartão de crédito", "04": "Cartão de débito",
    "05": "Crédito loja", "10": "Vale alimentação", "11": "Vale refeição",
    "12": "Vale presente", "13": "Vale combustível", "15": "Boleto bancário",
    "16": "Depósito bancário", "17": "PIX", "18": "Transferência", "90": "Sem pagamento",
    "99": "Outros",
}


@dataclass
class Fmt:
    """Escolhas de formatação numérica (parte do estilo sorteado)."""

    qty_decimals: int = 4
    unit_decimals: int = 4


# ---------------------------------------------------------------- formatters


def money(v, decimals: int = 2) -> str:
    try:
        n = float(v)
    except (TypeError, ValueError):
        return ""
    s = f"{n:,.{decimals}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_doc(doc: str) -> str:
    doc = (doc or "").strip()
    if len(doc) == 14:
        return f"{doc[:2]}.{doc[2:5]}.{doc[5:8]}/{doc[8:12]}-{doc[12:]}"
    if len(doc) == 11:
        return f"{doc[:3]}.{doc[3:6]}.{doc[6:9]}-{doc[9:]}"
    return doc


def fmt_cep(cep: str) -> str:
    cep = re.sub(r"\D", "", cep or "")
    return f"{cep[:5]}-{cep[5:]}" if len(cep) == 8 else cep


def fmt_fone(f: str) -> str:
    d = re.sub(r"\D", "", f or "")
    if len(d) == 11:
        return f"({d[:2]}) {d[2:7]}-{d[7:]}"
    if len(d) == 10:
        return f"({d[:2]}) {d[2:6]}-{d[6:]}"
    return d


def fmt_date(iso: str) -> str:
    iso = (iso or "").strip()
    try:
        return datetime.fromisoformat(iso).strftime("%d/%m/%Y")
    except ValueError:
        return iso


def fmt_time(iso: str) -> str:
    try:
        return datetime.fromisoformat((iso or "").strip()).strftime("%H:%M:%S")
    except ValueError:
        return ""


def fmt_datetime(iso: str) -> str:
    d, t = fmt_date(iso), fmt_time(iso)
    return f"{d} {t}".strip()


def fmt_nnf(n: str) -> str:
    n = re.sub(r"\D", "", n or "").zfill(9)
    return f"{n[:3]}.{n[3:6]}.{n[6:]}"


def fmt_chave(ch: str) -> str:
    ch = re.sub(r"\s", "", ch or "")
    return " ".join(ch[i : i + 4] for i in range(0, len(ch), 4))


# ---------------------------------------------------------------- xml helpers


def _strip_ns(root):
    for el in root.iter():
        if isinstance(el.tag, str):
            el.tag = etree.QName(el).localname
    return root


def _t(node, path: str, default: str = "") -> str:
    if node is None:
        return default
    r = node.find(path)
    if r is None or r.text is None:
        return default
    return r.text.strip()


def _party(node, addr_tag: str) -> dict:
    a = node.find(addr_tag) if node is not None else None
    street = ", ".join(x for x in (_t(a, "xLgr"), _t(a, "nro")) if x)
    cpl = _t(a, "xCpl")
    if cpl:
        street = f"{street} - {cpl}"
    doc = _t(node, "CNPJ") or _t(node, "CPF")
    return {
        "name": _t(node, "xNome"),
        "fantasy": _t(node, "xFant"),
        "doc": fmt_doc(doc),
        "ie": _t(node, "IE"),
        "street": street,
        "district": _t(a, "xBairro"),
        "city": _t(a, "xMun"),
        "uf": _t(a, "UF"),
        "cep": fmt_cep(_t(a, "CEP")),
        "phone": fmt_fone(_t(a, "fone")),
        "email": _t(node, "email"),
        "iest": _t(node, "IEST"),
        "cpl": _t(a, "xCpl"),
        "lgr_nro": ", ".join(x for x in (_t(a, "xLgr"), _t(a, "nro")) if x),
    }


def _loc(node) -> dict | None:
    """Retirada / entrega (mesmo grupo TLocal)."""
    if node is None:
        return None
    street = ", ".join(x for x in (_t(node, "xLgr"), _t(node, "nro")) if x)
    return {
        "name": _t(node, "xNome"),
        "doc": fmt_doc(_t(node, "CNPJ") or _t(node, "CPF")),
        "street": street,
        "district": _t(node, "xBairro"),
        "city": _t(node, "xMun"),
        "uf": _t(node, "UF"),
        "cep": fmt_cep(_t(node, "CEP")),
        "ie": _t(node, "IE"),
        "phone": fmt_fone(_t(node, "fone")),
    }


def _address_lines(p: dict) -> list[str]:
    """Bloco de endereço do emitente, como no DANFE real."""
    lines = [p["lgr_nro"]]
    if p["cpl"]:
        lines.append(p["cpl"])
    lines += [p["district"], f"{p['city']} - {p['uf']}", p["cep"], f"Fone: {p['phone']}"]
    return lines


# ---------------------------------------------------------------- main parse


def parse_nfe(xml: str | bytes, fmt: Fmt | None = None) -> dict:
    fmt = fmt or Fmt()
    raw = xml.encode("utf8") if isinstance(xml, str) else xml
    root = _strip_ns(etree.fromstring(raw))
    inf = root.find(".//infNFe")
    if inf is None:
        raise ValueError("XML sem <infNFe>")
    ide, emit, dest = inf.find("ide"), inf.find("emit"), inf.find("dest")
    prot = root.find(".//protNFe/infProt")
    tot = inf.find("total/ICMSTot")

    chave = re.sub(r"\D", "", inf.get("Id", "")[3:]) or _t(prot, "chNFe")
    tp_amb = _t(ide, "tpAmb") or _t(prot, "tpAmb")

    items = []
    for det in inf.findall("det"):
        p, imp = det.find("prod"), det.find("imposto")
        icms = imp.find("ICMS")[0] if imp is not None and imp.find("ICMS") is not None and len(imp.find("ICMS")) else None
        ipi = imp.find("IPI/IPITrib") if imp is not None else None
        extras = []
        info = _t(det, "infAdProd")
        if info:
            extras.append(info)
        rastros = []
        for r in det.findall("prod/rastro"):
            rastros.append(
                f"Lote: {_t(r, 'nLote')} Qtd: {money(_t(r, 'qLote'), fmt.qty_decimals)} "
                f"Fab: {fmt_date(_t(r, 'dFab'))} Val: {fmt_date(_t(r, 'dVal'))}"
            )
        anp = det.find("prod/comb")
        if anp is not None:
            rastros.append(
                f"cProdANP: {_t(anp, 'cProdANP')} descANP: {_t(anp, 'descANP')} UFCons: {_t(anp, 'UFCons')}"
            )
        med = det.find("prod/med")
        if med is not None:
            rastros.append(f"cProdANVISA: {_t(med, 'cProdANVISA')} PMC: {money(_t(med, 'vPMC'), fmt.qty_decimals)}")
        extras = rastros + extras  # ordem da lib: lote, ANP, ANVISA, infAdProd
        orig = _t(icms, "orig")
        cst = _t(icms, "CST") or _t(icms, "CSOSN")
        items.append(
            {
                "n": det.get("nItem", ""),
                "code": _t(p, "cProd"),
                "desc": _t(p, "xProd"),
                "extra": extras,
                "ncm": _t(p, "NCM"),
                "cst": f"{orig}{cst}" if cst else "",
                "cfop": _t(p, "CFOP"),
                "un": _t(p, "uCom"),
                "qty": money(_t(p, "qCom"), fmt.qty_decimals),
                "unit": money(_t(p, "vUnCom"), fmt.unit_decimals),
                "total": money(_t(p, "vProd")),
                "discount": money(_t(p, "vDesc")) if _t(p, "vDesc") else "",
                "bc": money(_t(icms, "vBC")) if icms is not None and icms.find("vBC") is not None else "0,00",
                "icms": money(_t(icms, "vICMS")) if icms is not None and icms.find("vICMS") is not None else "0,00",
                "ipi": money(_t(ipi, "vIPI")) if ipi is not None else "0,00",
                "p_icms": money(_t(icms, "pICMS")) if icms is not None and icms.find("pICMS") is not None else "0,00",
                "p_ipi": money(_t(ipi, "pIPI")) if ipi is not None else "0,00",
                "is_service": det.find("imposto/ISSQN") is not None,
            }
        )

    transp = inf.find("transp")
    tr = transp.find("transporta") if transp is not None else None
    veic = transp.find("veicTransp") if transp is not None else None
    vol = transp.find("vol") if transp is not None else None
    transport = {
        "mod": MOD_FRETE.get(_t(transp, "modFrete"), _t(transp, "modFrete")),
        "name": _t(tr, "xNome"),
        "doc": fmt_doc(_t(tr, "CNPJ") or _t(tr, "CPF")),
        "ie": _t(tr, "IE"),
        "address": _t(tr, "xEnder"),
        "city": _t(tr, "xMun"),
        "uf": _t(tr, "UF"),
        "plate": _t(veic, "placa"),
        "plate_uf": _t(veic, "UF"),
        "antt": _t(veic, "RNTC"),
        "qvol": _t(vol, "qVol"),
        "esp": _t(vol, "esp"),
        "marca": _t(vol, "marca"),
        "nvol": _t(vol, "nVol"),
        "peso_b": money(_t(vol, "pesoB"), 3) if vol is not None and vol.find("pesoB") is not None else "",
        "peso_l": money(_t(vol, "pesoL"), 3) if vol is not None and vol.find("pesoL") is not None else "",
    }

    dups = [
        {"n": _t(d, "nDup"), "due": fmt_date(_t(d, "dVenc")), "value": money(_t(d, "vDup"))}
        for d in inf.findall("cobr/dup")
    ]
    fat = inf.find("cobr/fat")

    payments = [
        {"type": TP_PAG.get(_t(d, "tPag"), _t(d, "tPag")), "value": money(_t(d, "vPag"))}
        for d in inf.findall("pag/detPag")
    ]

    issqn = inf.find("total/ISSQNtot")

    def tv(tag):
        return money(_t(tot, tag))

    emit_p = {**_party(emit, "enderEmit"), "crt": _t(emit, "CRT"), "im": _t(emit, "IM")}
    dest_p = _party(dest, "enderDest")
    dest_id_label = "CNPJ" if len(re.sub(r"\W", "", dest_p["doc"])) == 14 else "CPF"
    tot_nf = money(_t(tot, "vNF"))
    receipt_text = (
        f"RECEBEMOS DE {emit_p['name']} OS PRODUTOS/SERVIÇOS CONSTANTES DA NOTA FISCAL INDICADA ABAIXO. "
        f"EMISSÃO: {fmt_date(_t(ide, 'dhEmi'))} VALOR TOTAL: {tot_nf} "
        f"DESTINATARIO: {dest_p['name']} - {dest_p['lgr_nro']}, {dest_p['district']}, "
        f"{dest_p['city']} - {dest_p['uf']}, {dest_id_label}: {dest_p['doc']}"
    )
    return {
        "receipt_text": receipt_text,
        "simples": emit_p["crt"] in ("1", "4"),
        "tp_amb": tp_amb,
        "homolog": tp_amb == "2",
        "natop": _t(ide, "natOp"),
        "tp_nf": _t(ide, "tpNF") or "1",
        "numero": fmt_nnf(_t(ide, "nNF")),
        "numero_raw": _t(ide, "nNF"),
        "serie": _t(ide, "serie"),
        "chave": fmt_chave(chave),
        "chave_raw": chave,
        "emissao": fmt_date(_t(ide, "dhEmi")),
        "saida": fmt_date(_t(ide, "dhSaiEnt")),
        "hora_saida": fmt_time(_t(ide, "dhSaiEnt")),
        "protocolo": (
            f"{_t(prot, 'nProt')} - {fmt_datetime(_t(prot, 'dhRecbto'))}" if prot is not None else ""
        ),
        "emit": {**emit_p, "address_lines": _address_lines(emit_p)},
        "dest": dest_p,
        "retirada": _loc(inf.find("retirada")),
        "entrega": _loc(inf.find("entrega")),
        "products": items,
        "totals": {
            "bc_icms": tv("vBC"), "icms": tv("vICMS"), "bc_st": tv("vBCST"), "st": tv("vST"),
            "fcp": tv("vFCP"), "ii": tv("vII"), "pis": tv("vPIS"), "cofins": tv("vCOFINS"),
            "prod": tv("vProd"), "frete": tv("vFrete"), "seguro": tv("vSeg"), "desc": tv("vDesc"),
            "outras": tv("vOutro"), "ipi": tv("vIPI"), "nf": tv("vNF"),
            "trib": tv("vTotTrib") if tot is not None and tot.find("vTotTrib") is not None else "",
        },
        "issqn": (
            {
                "serv": money(_t(issqn, "vServ")), "bc": money(_t(issqn, "vBC")),
                "iss": money(_t(issqn, "vISS")),
            }
            if issqn is not None
            else None
        ),
        "transport": transport,
        "fatura": (
            {"n": _t(fat, "nFat"), "orig": money(_t(fat, "vOrig")), "desc": money(_t(fat, "vDesc")),
             "liq": money(_t(fat, "vLiq"))}
            if fat is not None
            else None
        ),
        "duplicatas": dups,
        "payments": payments,
        "inf_cpl_full": " ".join(
            f"{_t(inf, 'infAdic/infCpl')} {_t(inf, 'infAdic/infAdFisco')}".split()
        ),
        "inf_cpl": _t(inf, "infAdic/infCpl"),
        "inf_fisco": _t(inf, "infAdic/infAdFisco"),
    }
