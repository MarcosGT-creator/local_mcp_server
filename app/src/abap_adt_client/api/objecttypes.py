from ..http_request import HttpRequestParameters, request
import xml.etree.ElementTree as ET
from typing import Dict


def get_searchable_object_types(
    http_request_parameters: HttpRequestParameters,
) -> Dict[str, Dict[str, str]]:
    """
    Get list of all SAP object types available in the system for searching.
    This includes both creatable and non-creatable object types.
    
    Returns:
        Dictionary with object types and their descriptions, e.g.:
        {
            "CLAS/OC": {"type": "CLAS/OC", "description": "Class"},
            "PROG/P": {"type": "PROG/P", "description": "Program"},
            ...
        }
    """
    response = request(
        http_request_parameters=http_request_parameters,
        uri="/sap/bc/adt/repository/informationsystem/objecttypes",
        method="GET",
        body="",
        params={},
    )
    
    # Parse XML response
    root = ET.fromstring(response.text)
    
    # Extract object types
    result = {}
    ns = {'nameditem': 'http://www.sap.com/adt/nameditem'}
    
    for item in root.findall('.//nameditem:namedItem', ns):
        name_elem = item.find('nameditem:name', ns)
        description_elem = item.find('nameditem:description', ns)
        data_elem = item.find('nameditem:data', ns)
        
        if name_elem is not None and name_elem.text and data_elem is not None and data_elem.text:
            obj_type = data_elem.text.strip()
            # Skip group entries (WGRP) and empty entries
            if obj_type and obj_type != 'WGRP':
                desc_text = description_elem.text.strip() if description_elem is not None and description_elem.text else ""
                # Clean up multi-line descriptions (keep only first line)
                first_line = desc_text.split('\n')[0].strip() if desc_text else ""
                
                result[name_elem.text.strip()] = {
                    "type": obj_type,
                    "description": first_line
                }
    
    return result
