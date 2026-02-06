from typing import TypedDict, List, Optional, Dict, Any
import xml.etree.ElementTree as ET
from ..http_request import HttpRequestParameters, request


class TransportObject(TypedDict):
    """Information about an object in a transport."""
    PGMID: str           # Program ID (e.g., "LIMU", "R3TR")
    TYPE: str            # Object type (e.g., "CLAS", "METH", "DDLS")
    NAME: str            # Object name (preserves exact spacing for methods)
    OBJ_DESC: str        # Object description
    POSITION: str        # Position in transport (e.g., "000001")
    LOCK_STATUS: str     # Lock status ('X' = locked, '' = unlocked)
    IMG_ACTIVITY: str    # IMG activity


class TransportInfo(TypedDict):
    """Information about a transport request."""
    TRKORR: str          # Transport request number (e.g., "D2AK904079")
    DESCRIPTION: str     # Transport description
    TYPE: str            # Transport type (K=Workbench, W=Customizing)
    STATUS: str          # Status (D=Modifiable, R=Released, L=Locked)
    OWNER: str           # Owner/creator of the transport
    TARGET: str          # Target system (e.g., /ZNQUALIT/)
    CREATED_DATE: str    # Creation date
    CREATED_TIME: str    # Creation time
    URI: str             # Transport URI


class ListTransportsResult(TypedDict):
    """Result of listing transport requests."""
    TRANSPORTS: List[TransportInfo]
    TOTAL_COUNT: int


def _get_default_configuration(http_params: HttpRequestParameters) -> str:
    """Get the default configuration URI for the current user.
    
    This fetches the list of configurations and returns the first one,
    which is typically the user's default configuration.
    
    Args:
        http_params: HTTP request parameters
        
    Returns:
        Configuration URI (e.g., /sap/bc/adt/cts/transportrequests/searchconfiguration/configurations/CONFIGID)
    """
    response = request(
        http_params,
        uri="/sap/bc/adt/cts/transportrequests/searchconfiguration/configurations",
        method="GET",
        body="",
        params={},
        content_type=None,
        accept="application/vnd.sap.adt.configurations.v1+xml"
    )
    
    # Parse response to get first configuration URI
    namespaces = {
        'configurations': 'http://www.sap.com/adt/configurations',
        'configuration': 'http://www.sap.com/adt/configuration',
        'atom': 'http://www.w3.org/2005/Atom'
    }
    
    root = ET.fromstring(response.text)
    
    # Find first configuration link
    config_elem = root.find('.//configuration:configuration/atom:link[@rel="http://www.sap.com/adt/categories/configurations"]', namespaces)
    
    if config_elem is not None:
        config_uri = config_elem.get('href', '')
        return config_uri
    
    # If no configuration found, return empty (API will use defaults)
    return ""


def _parse_transports_list_response(xml_content: str) -> ListTransportsResult:
    """Parse XML response from list transports API.
    
    Args:
        xml_content: XML response from SAP
        
    Returns:
        ListTransportsResult with list of transports
    """
    # Parse with namespace handling
    # Note: SAP uses multiple possible namespaces for transport organizer
    namespaces = {
        'tm': 'http://www.sap.com/cts/adt/tm',  # Used in responses
        'adtcore': 'http://www.sap.com/adt/core'
    }
    
    root = ET.fromstring(xml_content)
    transports = []
    
    # The transport tree structure uses nested elements
    # Look for transport request elements - the element name is just "request", not "transportRequest"
    for tr in root.findall('.//tm:request', namespaces):
        # Get attributes with tm namespace
        transport_info: TransportInfo = {
            'TRKORR': tr.get('{http://www.sap.com/cts/adt/tm}number', ''),
            'DESCRIPTION': tr.get('{http://www.sap.com/cts/adt/tm}desc', ''),  # Changed from 'description' to 'desc'
            'TYPE': tr.get('{http://www.sap.com/cts/adt/tm}type', ''),
            'STATUS': tr.get('{http://www.sap.com/cts/adt/tm}status', ''),
            'OWNER': tr.get('{http://www.sap.com/cts/adt/tm}owner', ''),
            'TARGET': tr.get('{http://www.sap.com/cts/adt/tm}target', ''),
            'CREATED_DATE': '',
            'CREATED_TIME': '',
            'URI': tr.get('{http://www.sap.com/cts/adt/tm}uri', '')  # Changed from adtcore to tm namespace
        }
        
        # Parse lastchanged_timestamp if available (format: 20251027223030)
        lastchanged = tr.get('{http://www.sap.com/cts/adt/tm}lastchanged_timestamp', '')
        if lastchanged and len(lastchanged) >= 14:
            # Format: YYYYMMDDHHMMSS
            transport_info['CREATED_DATE'] = f"{lastchanged[0:4]}-{lastchanged[4:6]}-{lastchanged[6:8]}"
            transport_info['CREATED_TIME'] = f"{lastchanged[8:10]}:{lastchanged[10:12]}:{lastchanged[12:14]}"
        
        transports.append(transport_info)
    
    return {
        'TRANSPORTS': transports,
        'TOTAL_COUNT': len(transports)
    }


def list_transports(
    http_params: HttpRequestParameters,
    targets: bool = True,
    transport_number: Optional[str] = None
) -> ListTransportsResult:
    """List transport requests from SAP system.
    
    Fetches transport requests from the SAP Transport Organizer using the configuration-based approach
    that Eclipse ADT uses. This automatically fetches the user's default configuration and uses it
    to query transports.
    
    The filters (user, status, transport type) are determined by the user's saved configuration
    in Eclipse ADT. To change these filters, modify your configuration in Eclipse ADT's Transport
    Organizer view.
    
    Args:
        http_params: HTTP request parameters with session and base URL
        targets: Include target system information (default: True)
        transport_number: Optional transport number to filter by (e.g., 'D2AK904114').
                         Can include wildcards (*) for pattern matching.
        
    Returns:
        ListTransportsResult with list of transport requests matching the user's configuration
        
    Example:
        # List transports using user's default configuration
        result = list_transports(http_params)
        
        # List specific transport
        result = list_transports(http_params, transport_number='D2AK904114')
        
        # List transports with pattern
        result = list_transports(http_params, transport_number='D2AK9041*')
        
        for tr in result['TRANSPORTS']:
            print(f"{tr['TRKORR']}: {tr['DESCRIPTION']}")
        
    Note:
        Eclipse ADT uses a configuration-based approach where filter settings are stored
        in a configuration object. This function automatically fetches and uses the user's
        default configuration.
    """
    # Get the user's default configuration URI
    config_uri = _get_default_configuration(http_params)
    
    # Build query parameters using Eclipse's approach
    params = {
        "targets": "true" if targets else "false"
    }
    
    # Add configUri if we have one
    if config_uri:
        params["configUri"] = config_uri
    
    # Add transport number filter if provided
    if transport_number:
        params["trNumber"] = transport_number
    
    # Make GET request
    # Accept both v1 formats that Eclipse uses
    response = request(
        http_params,
        uri="/sap/bc/adt/cts/transportrequests",
        method="GET",
        body="",
        params=params,
        content_type=None,
        accept="application/vnd.sap.adt.transportorganizer.v1+xml, application/vnd.sap.adt.transportorganizertree.v1+xml"
    )
    
    return _parse_transports_list_response(response.text)


def get_transport_objects(
    http_params: HttpRequestParameters,
    transport_number: str
) -> List[TransportObject]:
    """Get all objects in a transport request.
    
    This retrieves objects from either a parent transport request or a child task.
    SAP automatically includes objects from both the parent TR and any unreleased child tasks.
    
    Args:
        http_params: HTTP request parameters
        transport_number: Transport request or task number (e.g., "DHAK905110", "DHAK905111")
        
    Returns:
        List of TransportObject dictionaries with object details
        
    Example:
        >>> objects = get_transport_objects(http_params, "DHAK905110")
        >>> for obj in objects:
        ...     print(f"{obj['TYPE']}: {obj['NAME']}")
    """
    # Register namespace
    ET.register_namespace('tm', 'http://www.sap.com/cts/adt/tm')
    
    # GET request to retrieve transport with objects
    response = request(
        http_params,
        uri=f"/sap/bc/adt/cts/transportrequests/{transport_number}",
        method="GET",
        body="",
        params={},
        content_type=None,
        accept="application/vnd.sap.adt.transportorganizer.v1+xml"
    )
    
    # Parse response to extract objects
    namespaces = {'tm': 'http://www.sap.com/cts/adt/tm'}
    root = ET.fromstring(response.text)
    
    objects: List[TransportObject] = []
    
    # Find all tm:abap_object elements (they can be nested in tm:request elements)
    # This handles both parent TR objects and child task objects
    for obj_elem in root.findall('.//tm:abap_object', namespaces):
        obj: TransportObject = {
            'PGMID': obj_elem.get('{http://www.sap.com/cts/adt/tm}pgmid', ''),
            'TYPE': obj_elem.get('{http://www.sap.com/cts/adt/tm}type', ''),
            'NAME': obj_elem.get('{http://www.sap.com/cts/adt/tm}name', ''),
            'OBJ_DESC': obj_elem.get('{http://www.sap.com/cts/adt/tm}obj_desc', ''),
            'POSITION': obj_elem.get('{http://www.sap.com/cts/adt/tm}position', ''),
            'LOCK_STATUS': obj_elem.get('{http://www.sap.com/cts/adt/tm}lock_status', ''),
            'IMG_ACTIVITY': obj_elem.get('{http://www.sap.com/cts/adt/tm}img_activity', '')
        }
        objects.append(obj)
    
    return objects
