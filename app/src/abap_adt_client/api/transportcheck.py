from typing import TypedDict, Optional, List
from ..http_request import HttpRequestParameters, request
import xml.etree.ElementTree as ET


class TransportRequest(TypedDict, total=False):
    """Information about a single transport request."""
    TRKORR: str          # Transport request number (e.g., "D2AK904079")
    TRFUNCTION: str      # Transport function (K=Workbench, W=Customizing)
    TRSTATUS: str        # Status (D=Development, R=Released)
    TARSYSTEM: str       # Target system
    AS4USER: str         # User who created the request
    AS4DATE: str         # Creation date (YYYY-MM-DD)
    AS4TIME: str         # Creation time (HH:MM:SS)
    AS4TEXT: str         # Transport description
    CLIENT: str          # Client number
    REPOID: str          # Repository ID


class TransportCheckResult(TypedDict, total=False):
    """Transport check result with object metadata and available transport requests."""
    # Object identification
    PGMID: str           # Program ID (e.g., "R3TR")
    OBJECT: str          # Object type (e.g., "CLAS", "DDLS")
    OBJECTNAME: str      # Object name (e.g., "ZCL_TEST")
    OPERATION: str       # Operation type
    
    # Package information
    DEVCLASS: str        # Development class/package
    CTEXT: str           # Package description
    PDEVCLASS: str       # Parent development class
    TADIRDEVC: str       # TADIR development class
    SUPER_PACKAGE: str   # Super package
    
    # Metadata
    KORRFLAG: str        # Correction flag (X=correction required)
    AS4USER: str         # Current user
    DLVUNIT: str         # Delivery unit
    NAMESPACE: str       # Namespace (e.g., "/0CUST/")
    RESULT: str          # Result status (S=Success)
    RECORDING: str       # Recording flag
    EXISTING_REQ_ONLY: str  # Existing requests only flag
    URI: str             # Object URI
    
    # Lists
    REQUESTS: List[TransportRequest]  # Available transport requests


class TransportCheckRequest(TypedDict, total=False):
    """Transport check request parameters. All fields are optional."""
    PGMID: str
    OBJECT: str
    OBJECTNAME: str
    DEVCLASS: str
    SUPER_PACKAGE: str
    OPERATION: str
    URI: str


def _build_transport_check_body(object_uri: str) -> str:
    """Build XML body for transport check request.
    
    Args:
        object_uri: URI of the object to check
        
    Returns:
        XML string for the request body
        
    Note:
        All other fields (PGMID, OBJECT, OBJECTNAME, etc.) are left empty
        and the SAP system automatically determines them from the URI.
    """
    return f"""<?xml version="1.0" encoding="UTF-8" ?>
        <asx:abap version="1.0" xmlns:asx="http://www.sap.com/abapxml">
            <asx:values>
                <DATA>
                    <PGMID></PGMID>
                    <OBJECT></OBJECT>
                    <OBJECTNAME></OBJECTNAME>
                    <DEVCLASS></DEVCLASS>
                    <SUPER_PACKAGE></SUPER_PACKAGE>
                    <OPERATION></OPERATION>
                    <URI>{object_uri}</URI>
                </DATA>
            </asx:values>
        </asx:abap>"""


def _parse_transport_check_response(xml_response: str) -> TransportCheckResult:
    """Parse transport check XML response into structured data.
    
    Args:
        xml_response: Raw XML response from transport check
        
    Returns:
        TransportCheckResult with parsed data
    """
    root = ET.fromstring(xml_response)
    data = root.find('.//DATA')
    
    if data is None:
        raise Exception("Invalid transport check response: DATA element not found")
    
    # Parse basic object information
    result: TransportCheckResult = {
        "PGMID": data.findtext("PGMID", ""),
        "OBJECT": data.findtext("OBJECT", ""),
        "OBJECTNAME": data.findtext("OBJECTNAME", ""),
        "OPERATION": data.findtext("OPERATION", ""),
        "DEVCLASS": data.findtext("DEVCLASS", ""),
        "CTEXT": data.findtext("CTEXT", ""),
        "KORRFLAG": data.findtext("KORRFLAG", ""),
        "AS4USER": data.findtext("AS4USER", ""),
        "PDEVCLASS": data.findtext("PDEVCLASS", ""),
        "DLVUNIT": data.findtext("DLVUNIT", ""),
        "NAMESPACE": data.findtext("NAMESPACE", ""),
        "SUPER_PACKAGE": data.findtext("SUPER_PACKAGE", ""),
        "RESULT": data.findtext("RESULT", ""),
        "RECORDING": data.findtext("RECORDING", ""),
        "EXISTING_REQ_ONLY": data.findtext("EXISTING_REQ_ONLY", ""),
        "TADIRDEVC": data.findtext("TADIRDEVC", ""),
        "URI": data.findtext("URI", ""),
        "REQUESTS": []
    }
    
    # Parse transport requests
    requests_elem = data.find("REQUESTS")
    if requests_elem is not None:
        for cts_req in requests_elem.findall("CTS_REQUEST"):
            req_header = cts_req.find("REQ_HEADER")
            if req_header is not None:
                transport_req: TransportRequest = {
                    "TRKORR": req_header.findtext("TRKORR", ""),
                    "TRFUNCTION": req_header.findtext("TRFUNCTION", ""),
                    "TRSTATUS": req_header.findtext("TRSTATUS", ""),
                    "TARSYSTEM": req_header.findtext("TARSYSTEM", ""),
                    "AS4USER": req_header.findtext("AS4USER", ""),
                    "AS4DATE": req_header.findtext("AS4DATE", ""),
                    "AS4TIME": req_header.findtext("AS4TIME", ""),
                    "AS4TEXT": req_header.findtext("AS4TEXT", ""),
                    "CLIENT": req_header.findtext("CLIENT", ""),
                    "REPOID": req_header.findtext("REPOID", ""),
                }
                result["REQUESTS"].append(transport_req)
    
    return result


def transport_check(
    http_request_parameters: HttpRequestParameters,
    object_uri: str,
) -> TransportCheckResult:
    """Perform a transport check for an SAP object.
    
    This checks which transport requests are available for the given object
    and returns transport-related metadata including a list of open transport
    requests that the user can select from.
    
    Args:
        http_request_parameters: HTTP request parameters
        object_uri: URI of the object (e.g., /sap/bc/adt/oo/classes/zcl_test/source/main)
        
    Returns:
        TransportCheckResult containing:
        - Object metadata (PGMID, OBJECT, OBJECTNAME, DEVCLASS, package info)
        - REQUESTS: List of available transport requests with:
          * TRKORR: Transport request number
          * AS4TEXT: Description
          * TRSTATUS: Status (D=Development, R=Released)
          * AS4DATE/AS4TIME: Creation date/time
          * AS4USER: Owner
        
    Example:
        >>> result = client.transport_check(object_uri="/sap/bc/adt/oo/classes/zcl_test/source/main")
        >>> print(f"Object: {result['OBJECTNAME']}, Package: {result['DEVCLASS']}")
        >>> print(f"Available transports: {len(result['REQUESTS'])}")
        >>> for req in result['REQUESTS']:
        ...     print(f"  {req['TRKORR']}: {req['AS4TEXT']}")
        
    Note:
        The SAP system automatically determines PGMID, OBJECT, OBJECTNAME, and 
        DEVCLASS from the URI, so only the URI needs to be provided.
        
        This is commonly used when an object is NOT yet locked in a transport.
        The LLM/user can then select from the list of available transports.
    """
    body = _build_transport_check_body(object_uri)
    
    # SAP ADT transport check content type and accept header
    content_type = "application/vnd.sap.as+xml; charset=UTF-8; dataname=com.sap.adt.transport.service.checkData"
    accept = "application/vnd.sap.as+xml;charset=UTF-8;dataname=com.sap.adt.transport.service.checkData"
    
    response = request(
        http_request_parameters=http_request_parameters,
        uri="/sap/bc/adt/cts/transportchecks",
        method="POST",
        body=body,
        params={},
        content_type=content_type,
        accept=accept,
    )
    
    if response.status_code == 200:
        return _parse_transport_check_response(response.text)
    else:
        raise Exception(
            f"{response.status_code} Failed to perform transport check for {object_uri}.\n{response.text}"
        )
