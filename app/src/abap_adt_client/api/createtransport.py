from typing import TypedDict, Literal
import xml.etree.ElementTree as ET
from ..http_request import HttpRequestParameters, request


class CreateTransportRequest(TypedDict, total=False):
    """Parameters for creating a new transport request (object-specific API)."""
    OPERATION: str
    DEVCLASS: str
    REQUEST_TEXT: str
    REF: str


class CreateTransportResult(TypedDict):
    """Result of creating a transport request."""
    TRKORR: str
    MESSAGE_SEVERITY: str
    MESSAGE_SHORT_TEXT: str
    MESSAGE_LONG_TEXT: str


class TransportOrganizerResult(TypedDict):
    """Result from Transport Organizer API for creating a transport request."""
    TRKORR: str
    DESCRIPTION: str
    TYPE: str
    TARGET: str
    TARGET_DESC: str
    URI: str
    TASK_NUMBER: str
    TASK_OWNER: str
    TASK_URI: str


def _build_transport_organizer_body(
    description: str,
    target: str = "",
    tr_type: str = "K",
    owner: str = "",
) -> str:
    """Build XML body for Transport Organizer create request.
    
    Args:
        description: Description of the transport request
        target: Target system (e.g., /ZNQUALIT/, /ZPRD/)
        tr_type: Transport type - "K" for Workbench, "W" for Customizing
        owner: Task owner (REQUIRED - must be provided by caller, usually current username)
        
    Returns:
        XML string for the request body
        
    Note:
        The tm:owner attribute is REQUIRED for SAP to create the child task.
        Without it, SAP only creates the parent transport request.
    """
    # Owner is required for creating child task
    if not owner:
        raise ValueError("Owner is required for creating transport with child task. Pass username from adt_client.")
    
    return f"""<?xml version="1.0" encoding="ASCII"?>
        <tm:root xmlns:tm="http://www.sap.com/cts/adt/tm" tm:useraction="newrequest">
        <tm:request tm:desc="{description}" tm:type="{tr_type}" tm:target="{target}" tm:cts_project="">
            <tm:task tm:owner="{owner}"/>
        </tm:request>
        </tm:root>"""


def _parse_transport_organizer_response(xml_response: str) -> TransportOrganizerResult:
    """Parse Transport Organizer XML response.
    
    Args:
        xml_response: Raw XML response from Transport Organizer
        
    Returns:
        TransportOrganizerResult with transport details including child task
    """
    
    # Register namespace
    ET.register_namespace('tm', 'http://www.sap.com/cts/adt/tm')
    root = ET.fromstring(xml_response)
    
    # Define namespace
    ns = {'tm': 'http://www.sap.com/cts/adt/tm'}
    
    request_elem = root.find('.//tm:request', ns)
    if request_elem is None:
        raise Exception("Invalid Transport Organizer response: request element not found")
    
    # Extract task information (child task)
    task_elem = request_elem.find('.//tm:task', ns)
    task_number = ''
    task_owner = ''
    task_uri = ''
    
    if task_elem is not None:
        task_number = task_elem.get('{http://www.sap.com/cts/adt/tm}number', '')
        task_owner = task_elem.get('{http://www.sap.com/cts/adt/tm}owner', '')
        task_uri = task_elem.get('{http://www.sap.com/cts/adt/tm}uri', '')
    
    result: TransportOrganizerResult = {
        "TRKORR": request_elem.get('{http://www.sap.com/cts/adt/tm}number', ''),
        "DESCRIPTION": request_elem.get('{http://www.sap.com/cts/adt/tm}desc', ''),
        "TYPE": request_elem.get('{http://www.sap.com/cts/adt/tm}type', ''),
        "TARGET": request_elem.get('{http://www.sap.com/cts/adt/tm}target', ''),
        "TARGET_DESC": request_elem.get('{http://www.sap.com/cts/adt/tm}target_desc', ''),
        "URI": request_elem.get('{http://www.sap.com/cts/adt/tm}uri', ''),
        "TASK_NUMBER": task_number,
        "TASK_OWNER": task_owner,
        "TASK_URI": task_uri,
    }
    
    return result


def _build_create_transport_body(
    devclass: str,
    request_text: str,
    ref: str,
    operation: str = "",
) -> str:
    """Build XML body for create transport request.
    
    Args:
        devclass: Development class/package (e.g., ZSAP_LLM_API)
        request_text: Description of the transport request
        ref: Reference URI of the object (e.g., /sap/bc/adt/oo/classes/zcl_test/source/main)
        operation: Operation type (usually empty)
        
    Returns:
        XML string for the request body
    """
    return f"""<?xml version="1.0" encoding="UTF-8" ?>
<asx:abap version="1.0" xmlns:asx="http://www.sap.com/abapxml">
    <asx:values>
        <DATA>
            <OPERATION>{operation}</OPERATION>
            <DEVCLASS>{devclass}</DEVCLASS>
            <REQUEST_TEXT>{request_text}</REQUEST_TEXT>
            <REF>{ref}</REF>
        </DATA>
    </asx:values>
</asx:abap>"""


def _parse_create_transport_response(xml_response: str) -> CreateTransportResult:
    """Parse create transport XML response into structured data.
    
    Args:
        xml_response: Raw XML response from create transport
        
    Returns:
        CreateTransportResult with TRKORR and message information
    """
    root = ET.fromstring(xml_response)
    data = root.find('.//DATA')
    
    if data is None:
        raise Exception("Invalid create transport response: DATA element not found")
    
    # Parse the transport number
    trkorr = data.findtext("TRKORR", "")
    
    # Parse message information
    message = data.find("MESSAGE")
    if message is not None:
        severity = message.findtext("SEVERITY", "")
        short_text = message.findtext("SHORT_TEXT", "")
        long_text = message.findtext("LONG_TEXT", "")
    else:
        severity = ""
        short_text = ""
        long_text = ""
    
    result: CreateTransportResult = {
        "TRKORR": trkorr,
        "MESSAGE_SEVERITY": severity,
        "MESSAGE_SHORT_TEXT": short_text,
        "MESSAGE_LONG_TEXT": long_text,
    }
    
    return result


def create_transport(
    http_request_parameters: HttpRequestParameters,
    devclass: str,
    request_text: str,
    ref: str,
    operation: str = "",
) -> CreateTransportResult:
    """Create a new transport request.
    
    This creates a new workbench transport request that can be used to
    transport object modifications across SAP systems.
    
    Args:
        http_request_parameters: HTTP request parameters
        devclass: Development class/package (e.g., ZSAP_LLM_API, $TMP for local)
        request_text: Description/text for the transport request (e.g., "Bug fix for class ZCL_TEST")
        ref: Reference URI of the object (e.g., /sap/bc/adt/oo/classes/zcl_test/source/main)
        operation: Operation type (optional, usually empty)
        
    Returns:
        CreateTransportResult containing:
        - TRKORR: The newly created transport request number (e.g., "D2AK904081")
        - MESSAGE_SEVERITY: Message severity if any (empty for success)
        - MESSAGE_SHORT_TEXT: Short message text if any
        - MESSAGE_LONG_TEXT: Long message text if any
        
    Example:
        >>> result = client.create_transport(
        ...     devclass="ZSAP_LLM_API",
        ...     request_text="Fix bug in API class",
        ...     ref="/sap/bc/adt/oo/classes/zcl_api/source/main"
        ... )
        >>> print(f"Created transport: {result['TRKORR']}")
        
    Note:
        This is typically called after transport_check() when the user wants
        to create a new transport request instead of using an existing one.
        
        After creating the transport, you would typically:
        1. Use the returned TRKORR to assign objects to it
        2. Lock the object (which will now associate it with this transport)
        3. Modify the object
        4. Save and activate
    """
    body = _build_create_transport_body(devclass, request_text, ref, operation)
    
    # SAP ADT create transport content type and accept headers
    content_type = "application/vnd.sap.as+xml; charset=UTF-8; dataname=com.sap.adt.CreateCorrectionRequest.v1"
    accept = "application/vnd.sap.as+xml;charset=UTF-8;dataname=com.sap.adt.CorrectionRequestResult, text/plain"
    
    response = request(
        http_request_parameters=http_request_parameters,
        uri="/sap/bc/adt/cts/transports",
        method="POST",
        body=body,
        params={},
        content_type=content_type,
        accept=accept,
    )
    
    if response.status_code == 200:
        return _parse_create_transport_response(response.text)
    else:
        raise Exception(
            f"{response.status_code} Failed to create transport request.\n{response.text}"
        )


def create_transport_organizer(
    http_request_parameters: HttpRequestParameters,
    description: str,
    target: str = "",
    tr_type: Literal["K", "W"] = "K",
    owner: str = "",
) -> TransportOrganizerResult:
    """Create a new transport request via Transport Organizer API.
    
    This is a pure/generic transport creation API that's NOT tied to a specific
    object. Use this when you want to create a transport request independently
    (e.g., from Transport Organizer view).
    
    Args:
        http_request_parameters: HTTP request parameters
        description: Description of the transport request (e.g., "Bug fixes for API")
        target: Target system (default: "/ZNQUALIT/", use "/ZPRD/" for production)
        tr_type: Transport type - "K" for Workbench (default), "W" for Customizing
        owner: Task owner username (optional, defaults to current user)
        
    Returns:
        TransportOrganizerResult containing:
        - TRKORR: The newly created transport request number
        - DESCRIPTION: Transport description
        - TYPE: Transport type (K or W)
        - TARGET: Target system
        - URI: Object URI in workbench
        
    Example:
        >>> result = client.create_transport_organizer(
        ...     description="API bug fixes",
        ...     target="/ZNQUALIT/"
        ... )
        >>> print(f"Created transport: {result['TRKORR']}")
        
    Note:
        This is different from create_transport() which is object-specific.
        Use this when:
        - Creating a transport from Transport Organizer
        - Creating a transport NOT tied to a specific object initially
        - You want a cleaner, simpler transport creation API
        
        The response includes HTTP status 201 (Created) on success.
    """
    body = _build_transport_organizer_body(description, target, tr_type, owner)
    
    # Transport Organizer API headers
    content_type = "text/plain"
    accept = "application/vnd.sap.adt.transportorganizer.v1+xml"
    
    response = request(
        http_request_parameters=http_request_parameters,
        uri="/sap/bc/adt/cts/transportrequests",
        method="POST",
        body=body,
        params={},
        content_type=content_type,
        accept=accept,
    )
    
    if response.status_code == 201:  # Created
        # Parse initial response to get TRKORR
        initial_result = _parse_transport_organizer_response(response.text)
        trkorr = initial_result["TRKORR"]
        
        # Make follow-up GET request to retrieve full details including child task
        try:
            get_response = request(
                http_request_parameters=http_request_parameters,
                uri=f"/sap/bc/adt/cts/transportrequests/{trkorr}",
                method="GET",
                body="",
                params={},
                content_type="",
                accept="application/vnd.sap.adt.transportorganizer.v1+xml",
            )
            
            if get_response.status_code == 200:
                # Parse the full response with task information
                return _parse_transport_organizer_response(get_response.text)
            else:
                # If GET fails, return initial result (without task info)
                return initial_result
                
        except Exception as e:
            # If GET fails, return initial result
            return initial_result
    else:
        raise Exception(
            f"{response.status_code} Failed to create transport request via Transport Organizer.\n{response.text}"
        )
