from ..http_request import HttpRequestParameters, request
from ..response_parsing import find_xml_elements_attributes
from typing import List, Dict, Optional


def search_object(
    http_request_parameters: HttpRequestParameters, 
    query: str, 
    max_results: int = 1,
    object_type: Optional[str] = None
) -> List[Dict[str, str]]:

    params = {
        "operation": "quickSearch", 
        "query": query, 
        "maxResults": max_results
    }
    
    # Add objectType parameter if specified (e.g., "CLAS/OC", "PROG/P", "TABL/DT")
    if object_type:
        params["objectType"] = object_type
    
    response = request(
        http_request_parameters=http_request_parameters,
        uri="/sap/bc/adt/repository/informationsystem/search",
        method="GET",
        body="",
        params=params,
    )
    elements = find_xml_elements_attributes(response.text, "adtcore:objectReference")
    return elements
