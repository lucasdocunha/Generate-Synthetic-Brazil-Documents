"""Primitivas genéricas de manipulação de XML por template, reaproveitáveis
por qualquer tipo de documento (PLANO_GERADOR.md secao 6).

Este módulo não conhece nada específico de DANFE/DACTE/etc — só sabe
localizar elementos/atributos por caminho relativo (com namespace) e clonar
subárvores repetíveis. A orquestração específica de cada tipo de documento
(quais campos existem, como ficam consistentes entre si) vive no adaptador
de cada tipo (ex.: generator/danfe.py), não aqui.
"""

import xml.etree.ElementTree as ET
from pathlib import Path


def load_template(path) -> ET.ElementTree:
    return ET.parse(Path(path))


def qualify(relative_path: str, namespace_uri: str) -> str:
    """'infNFe/emit/CNPJ' -> 'ns:infNFe/ns:emit/ns:CNPJ' (para uso com find()).

    O namespace real (URI) fica em {"ns": namespace_uri}, passado a find/findall.
    """
    parts = [p for p in relative_path.split("/") if p]
    return "/".join(f"ns:{p}" for p in parts)


def find_one(root: ET.Element, relative_path: str, namespace_uri: str) -> ET.Element:
    el = root.find(qualify(relative_path, namespace_uri), {"ns": namespace_uri})
    if el is None:
        raise ValueError(f"Caminho não encontrado no template: {relative_path!r}")
    return el


def set_text(root: ET.Element, relative_path: str, namespace_uri: str, value) -> None:
    find_one(root, relative_path, namespace_uri).text = str(value)


def set_attr(
    root: ET.Element, relative_path: str, namespace_uri: str, attr: str, value
) -> None:
    find_one(root, relative_path, namespace_uri).set(attr, str(value))


def clone_repeatable(
    root: ET.Element,
    parent_path: str,
    item_tag: str,
    namespace_uri: str,
    count: int,
) -> list:
    """Clona o primeiro elemento <item_tag> sob parent_path, count vezes,
    substituindo o(s) original(is). Retorna a lista de clones inseridos, na
    ordem, prontos para serem preenchidos pelo chamador.
    """
    parent = find_one(root, parent_path, namespace_uri) if parent_path else root
    qtag = f"{{{namespace_uri}}}{item_tag}"

    children = list(parent)
    originals = [child for child in children if child.tag == qtag]
    if not originals:
        raise ValueError(f"Nenhum elemento <{item_tag}> encontrado sob {parent_path!r}")
    template_item = originals[0]
    insert_index = children.index(originals[0])

    for child in originals:
        parent.remove(child)

    clones = []
    for i in range(count):
        clone = _deep_copy_element(template_item)
        parent.insert(insert_index + i, clone)
        clones.append(clone)
    return clones


def _deep_copy_element(el: ET.Element) -> ET.Element:
    import copy

    return copy.deepcopy(el)


def set_address(
    root: ET.Element,
    base_path: str,
    addr: dict,
    namespace_uri: str,
    include_complement: bool = True,
) -> None:
    """Preenche um bloco de endereço padrão (xLgr/nro/xCpl?/xBairro/cMun/xMun/UF/CEP)
    reaproveitado por todos os tipos de documento (DANFE, DACTE, DAMDFE)."""
    set_text(root, f"{base_path}/xLgr", namespace_uri, addr["street"])
    set_text(root, f"{base_path}/nro", namespace_uri, addr["number"])
    if include_complement:
        try:
            set_text(root, f"{base_path}/xCpl", namespace_uri, addr["complement"])
        except ValueError:
            pass  # template não tem xCpl neste bloco — sem problema
    set_text(root, f"{base_path}/xBairro", namespace_uri, addr["neighborhood"])
    set_text(root, f"{base_path}/cMun", namespace_uri, addr["municipality_code"])
    set_text(root, f"{base_path}/xMun", namespace_uri, addr["municipality_name"])
    set_text(root, f"{base_path}/UF", namespace_uri, addr["uf"])
    set_text(root, f"{base_path}/CEP", namespace_uri, addr["cep"])


def to_string(tree_or_root) -> str:
    root = tree_or_root.getroot() if hasattr(tree_or_root, "getroot") else tree_or_root
    return ET.tostring(root, encoding="unicode")


def find_optional(root: ET.Element, relative_path: str, namespace_uri: str):
    return root.find(qualify(relative_path, namespace_uri), {"ns": namespace_uri})


def remove(root: ET.Element, relative_path: str, namespace_uri: str) -> None:
    """Remove o elemento em `relative_path` (poda de template maximal).
    Silencioso se o caminho não existir. O pai é localizado pelo prefixo
    do caminho, ou é o próprio `root` para caminhos de um nível."""
    parts = [p for p in relative_path.split("/") if p]
    parent = find_optional(root, "/".join(parts[:-1]), namespace_uri) if len(parts) > 1 else root
    if parent is None:
        return
    child = parent.find(f"{{{namespace_uri}}}{parts[-1]}")
    if child is not None:
        parent.remove(child)


def sub(parent: ET.Element, tag: str, namespace_uri: str, text=None) -> ET.Element:
    """Cria <tag> filho de `parent` (no namespace), com texto opcional."""
    el = ET.SubElement(parent, f"{{{namespace_uri}}}{tag}")
    if text is not None:
        el.text = str(text)
    return el


def sub_fields(parent: ET.Element, namespace_uri: str, pairs) -> None:
    """Atalho: cria filhos em ordem a partir de [(tag, texto), ...]."""
    for tag, text in pairs:
        sub(parent, tag, namespace_uri, text)
