from ..http_request import HttpRequestParameters, request
from typing import Optional


def get_package_contents(
    http_request_parameters: HttpRequestParameters,
    package_name: str,
    object_search_pattern: str = "*",
    group_filter: Optional[str] = None,
    type_filter: Optional[str] = None,
) -> str:
    """
    Fetch objects from a package using the virtual folders API.
    
    This API supports hierarchical exploration:
    1. First call with just package_name returns groups (CORE_DATA_SERVICES, SOURCE_LIBRARY, etc.)
    2. Second call with package_name + group returns types (DDLS, CLAS, PROG, etc.)
    3. Third call with package_name + group + type returns actual objects
    
    Args:
        http_request_parameters: HTTP request parameters
        package_name: Name of the package (e.g., "ZGET_SUBS_API")
        object_search_pattern: Pattern for object names (default: "*")
        group_filter: Optional group filter (e.g., "CORE_DATA_SERVICES", "SOURCE_LIBRARY")
        type_filter: Optional type filter (e.g., "DDLS", "CLAS", "PROG")
    
    Returns:
        XML string with virtual folders result
    """
    
    # Build XML request body
    xml_parts = ['<?xml version="1.0" encoding="UTF-8"?>']
    xml_parts.append('<vfs:virtualFoldersRequest xmlns:vfs="http://www.sap.com/adt/ris/virtualFolders"')
    xml_parts.append(f' objectSearchPattern="{object_search_pattern}">')
    
    # Add package preselection (always required)
    xml_parts.append('  <vfs:preselection facet="package">')
    xml_parts.append(f'    <vfs:value>{package_name}</vfs:value>')
    xml_parts.append('  </vfs:preselection>')
    
    # Add group filter if specified
    if group_filter:
        xml_parts.append('  <vfs:preselection facet="group">')
        xml_parts.append(f'    <vfs:value>{group_filter}</vfs:value>')
        xml_parts.append('  </vfs:preselection>')
    
    # Add type filter if specified
    if type_filter:
        xml_parts.append('  <vfs:preselection facet="type">')
        xml_parts.append(f'    <vfs:value>{type_filter}</vfs:value>')
        xml_parts.append('  </vfs:preselection>')
    
    # Add facet order based on what filters are already applied
    xml_parts.append('  <vfs:facetorder>')
    if not group_filter:
        xml_parts.append('    <vfs:facet>group</vfs:facet>')
        xml_parts.append('    <vfs:facet>type</vfs:facet>')
    elif not type_filter:
        xml_parts.append('    <vfs:facet>type</vfs:facet>')
    # If both filters are specified, facetorder is empty (we get objects)
    xml_parts.append('  </vfs:facetorder>')
    
    xml_parts.append('</vfs:virtualFoldersRequest>')
    
    body = '\n'.join(xml_parts)
    
    response = request(
        http_request_parameters=http_request_parameters,
        uri="/sap/bc/adt/repository/informationsystem/virtualfolders/contents",
        method="POST",
        body=body,
        params={},
        content_type="application/vnd.sap.adt.repository.virtualfolders.request.v1+xml",
        accept="application/vnd.sap.adt.repository.virtualfolders.result.v1+xml"
    )
    
    return response.text
