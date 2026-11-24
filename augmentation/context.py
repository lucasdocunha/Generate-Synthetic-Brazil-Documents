"""Contexto de augmentation por tipo de documento.

Cada tipo informa ao `compose_document_artifacts` quem é o emitente (para
carimbos/POS coerentes), data, valor, qual `field_id` o carimbo de CNPJ cobre
e se o layout tem canhoto (assinatura no topo). Antes isso era adivinhado
por nomes de chaves de `field_values` (e caía em um "posto" fictício).
"""

from __future__ import annotations

_DEFAULT_ADDR = {
    "street": "AV. RIO BAHIA", "number": "8600", "neighborhood": "CENTRO",
    "cep": "36880000", "municipality_name": "MURIAE", "uf": "MG",
}


def _date_br(dh: str | None, default: str = "27/04/2024") -> str:
    if not dh:
        return default
    ymd = str(dh).split("T")[0].split("-")
    return f"{ymd[2]}/{ymd[1]}/{ymd[0]}" if len(ymd) == 3 else default


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _ctx(cnpj, name, address, dh, amount, field_id, has_receipt):
    return {
        "cnpj": cnpj or "02963955000170",
        "name": name or "AUTO POSTO BRASIL LTDA",
        "address": {**_DEFAULT_ADDR, **(address or {})},
        "date_br": _date_br(dh),
        "amount": _num(amount),  # None -> sem comprovante POS
        "cnpj_field_id": field_id,
        "has_receipt": has_receipt,
    }


def ctx_danfe(fv):
    return _ctx(fv.get("emit_cnpj"), fv.get("emit_xNome"), fv.get("emit_endereco"),
                fv.get("dhEmi"), fv.get("total_vNF"), "emit_cnpj_cpf", True)


def ctx_nfe_portal(fv):
    return {**ctx_danfe(fv), "has_receipt": False}


def ctx_dacte(fv):
    e = fv.get("emit") or {}
    return _ctx(e.get("cnpj"), e.get("xNome"), e.get("endereco"), fv.get("dhEmi"),
                fv.get("v_frete"), "emit_cnpj", True)


def ctx_damdfe(fv):
    return _ctx(fv.get("emit_cnpj"), fv.get("emit_xNome"), fv.get("emit_endereco"),
                fv.get("dhEmi"), fv.get("v_carga"), "emit_cnpj", False)


def ctx_danfse(fv):
    addr = {"municipality_name": str(fv.get("municipality_name") or "").upper() or "MURIAE"}
    return _ctx(fv.get("emit_cnpj"), fv.get("emit_xNome"), addr, fv.get("dhEmi"),
                fv.get("vServ"), "emit_cnpj", False)


def ctx_dacce(fv):
    e = fv.get("emitente") or {}
    addr = {"street": e.get("end"), "number": "", "neighborhood": e.get("bairro"),
            "municipality_name": e.get("cidade"), "uf": e.get("uf")}
    addr = {k: v for k, v in addr.items() if v}
    # CC-e não tem valor monetário: sem comprovante POS
    return _ctx(fv.get("autor_cnpj"), e.get("nome"), addr, fv.get("dh_evento"), None, "autor_cnpj", False)


def ctx_nfse_legado(fv):
    addr = {"municipality_name": str(fv.get("municipality_name") or "").upper() or "MURIAE"}
    return _ctx(fv.get("cnpj_prestador"), fv.get("razao_social_prestador") or fv.get("razao_social_tomador"),
                addr, fv.get("dEmissao"), fv.get("v_serv"), "cnpj_prestador", False)


CONTEXT_FNS = {
    "danfe": ctx_danfe, "nfe_portal": ctx_nfe_portal, "dacte": ctx_dacte, "damdfe": ctx_damdfe,
    "danfse": ctx_danfse, "dacce": ctx_dacce, "nfse_legado": ctx_nfse_legado,
}


def guess_context(fv: dict) -> dict:
    """Compatibilidade: adivinha o contexto por nomes de chaves (comportamento
    anterior). Os tipos registrados usam `CONTEXT_FNS`."""
    emit = fv.get("emit") or {}
    emitente = fv.get("emitente") or {}
    cnpj = fv.get("emit_cnpj") or emit.get("cnpj") or fv.get("autor_cnpj")
    name = fv.get("emit_xNome") or emit.get("xNome") or emitente.get("nome")
    addr = fv.get("emit_endereco") or emit.get("endereco")
    amount = fv.get("total_vNF") or fv.get("v_frete") or fv.get("vServ") or fv.get("v_carga") or 150.0
    return _ctx(cnpj, name, addr, fv.get("dhEmi") or fv.get("dh_evento"), amount, "emit_cnpj_cpf", True)
