from xml.etree import ElementTree as et
from typing import Optional, Dict, List
from .api.xml_namespaces import XML_NAMESPACES


def _strip_namespace(name: str) -> str:
    if name.startswith("{"):
        return name.split("}", 1)[1]
    if ":" in name:
        return name.split(":", 1)[1]
    return name


def _et_to_attributes_dict(element: Optional[et.Element]) -> Dict[str, str]:
    cleaned = (
        {_strip_namespace(key): value for key, value in element.attrib.items()}
        if element is not None
        else {}
    )
    return cleaned


def find_xml_elements_attributes(xml_text: str, tag_name: str) -> List[Dict[str, str]]:
    root = et.fromstring(xml_text)
    elements = root.findall(tag_name, XML_NAMESPACES)
    processed_elements = []
    for element in elements:
        cleaned = _et_to_attributes_dict(element)
        processed_elements.append(cleaned)
    return processed_elements


def find_xml_element_attributes(xml_text: str, tag_name: str) -> Dict[str, str]:
    root = et.fromstring(xml_text)
    element = root.find(tag_name, XML_NAMESPACES)
    element = _et_to_attributes_dict(element)
    return element


def find_xml_element_text(xml_text: str, tag_name: str):
    root = et.fromstring(xml_text)
    el = root.find(tag_name, XML_NAMESPACES)
    return "".join(el.itertext()).strip() if el is not None else ""


def parse_virtual_folders_result(xml_text: str) -> List[Dict[str, str]]:
    """
    Parse virtual folders result XML and extract folders and objects.
    
    Returns a list of dictionaries, where each dict represents either:
    - A virtual folder (group or type) with keys: name, displayName, facet, counter, hasChildrenOfSameFacet
    - An object with keys: name, text, uri, type, package, expandable
    """
    root = et.fromstring(xml_text)
    results = []
    
    # Parse virtual folders (groups or types)
    folders = root.findall("vfs:virtualFolder", XML_NAMESPACES)
    for folder in folders:
        folder_dict = _et_to_attributes_dict(folder)
        folder_dict["_type"] = "folder"
        results.append(folder_dict)
    
    # Parse objects (actual SAP objects like classes, CDS views, etc.)
    objects = root.findall("vfs:object", XML_NAMESPACES)
    for obj in objects:
        obj_dict = _et_to_attributes_dict(obj)
        obj_dict["_type"] = "object"
        results.append(obj_dict)
    
    return results
