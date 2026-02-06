from typing import TypedDict, Optional, Dict, List, Any
from ..http_request import HttpRequestParameters, request
from ..response_parsing import find_xml_element_text


# SAP ADT lock Accept header (matches Eclipse ADT exactly)
_LOCK_ACCEPT_HEADER = (
    "application/vnd.sap.as+xml;charset=UTF-8;dataname=com.sap.adt.lock.result;q=0.8, "
    "application/vnd.sap.as+xml;charset=UTF-8;dataname=com.sap.adt.lock.result2;q=0.9"
)


class LockResult(TypedDict, total=False):
    """Result data from a lock operation.
    
    Attributes:
        LOCK_HANDLE: Lock handle required for unlock and modify operations
        CORRNR: Transport request number (if object is already in a transport)
        CORRUSER: User who owns the transport request
        CORRTEXT: Description of the transport request
        IS_LOCAL: Whether object is in a local package (X or empty)
        IS_LINK_UP: Link-up mode indicator
        MODIFICATION_SUPPORT: Modification support level
    """
    LOCK_HANDLE: str
    CORRNR: str
    CORRUSER: str
    CORRTEXT: str
    IS_LOCAL: str
    IS_LINK_UP: str
    MODIFICATION_SUPPORT: str


def lock(http_request_parameters: HttpRequestParameters, object_uri: str) -> LockResult:
    """Lock an SAP object for editing.
    
    Args:
        http_request_parameters: HTTP request parameters
        object_uri: URI of the object to lock
        
    Returns:
        LockResult dictionary containing:
        - LOCK_HANDLE: Required for unlock/modify operations
        - CORRNR: Transport request number (if object already in transport)
        - CORRUSER: Transport request owner
        - CORRTEXT: Transport request description
        - IS_LOCAL: 'X' if local package, empty otherwise
        - Other metadata fields
        
    Raises:
        Exception: If lock fails (e.g., locked by another user)
        
    Example:
        >>> result = client.lock("/sap/bc/adt/oo/classes/zcl_test")
        >>> print(f"Lock handle: {result['LOCK_HANDLE']}")
        >>> if result.get('CORRNR'):
        >>>     print(f"Already in transport: {result['CORRNR']}")
        
    Note:
        Eclipse ADT does NOT send a Content-Type header for lock requests.
        Only the Accept header is sent with the SAP ADT lock result format.
    """
    response = request(
        http_request_parameters=http_request_parameters,
        uri=object_uri,
        body="",
        params={"_action": "LOCK", "accessMode": "MODIFY"},
        method="POST",
        content_type=None,  # No Content-Type header for lock requests
        accept=_LOCK_ACCEPT_HEADER,
    )
    if response.status_code == 200:
        # Parse the full response to extract all lock information
        import xml.etree.ElementTree as ET
        root = ET.fromstring(response.text)
        data = root.find('.//DATA')
        
        result: LockResult = {}
        if data is not None:
            # Extract all available fields
            result['LOCK_HANDLE'] = data.findtext('LOCK_HANDLE', '')
            result['CORRNR'] = data.findtext('CORRNR', '')
            result['CORRUSER'] = data.findtext('CORRUSER', '')
            result['CORRTEXT'] = data.findtext('CORRTEXT', '')
            result['IS_LOCAL'] = data.findtext('IS_LOCAL', '')
            result['IS_LINK_UP'] = data.findtext('IS_LINK_UP', '')
            result['MODIFICATION_SUPPORT'] = data.findtext('MODIFICATION_SUPPORT', '')
        
        if not result.get('LOCK_HANDLE'):
            raise Exception(f"Failed to extract lock handle from response.\n{response.text}")
            
        return result
    else:
        raise Exception(
            f"{response.status_code} Failed to lock {object_uri}.\n{response.text}"
        )


def unlock(
    http_request_parameters: HttpRequestParameters, object_uri: str, lock_handle: str
) -> bool:
    """Unlock an SAP object after editing.
    
    Args:
        http_request_parameters: HTTP request parameters
        object_uri: URI of the object to unlock
        lock_handle: Lock handle obtained from lock()
        
    Returns:
        True if successful
        
    Note:
        Unlock uses text/plain content-type as per SAP ADT standards.
    """
    response = request(
        http_request_parameters=http_request_parameters,
        uri=object_uri,
        body="",
        params={"_action": "UNLOCK", "lockHandle": lock_handle},
        method="POST",
        content_type="text/plain; charset=utf-8",
        accept=_LOCK_ACCEPT_HEADER,
    )
    if response.status_code == 200:
        return True
    else:
        raise Exception(
            f"{response.status_code} Failed to unlock {object_uri}\n{response.text}"
        )


def check_objects_lockable(
    http_request_parameters: HttpRequestParameters, 
    objects: List[Dict[str, str]]
) -> Dict[str, Any]:
    """
    Check if objects can be locked (i.e., not currently locked by anyone).
    
    This function attempts to lock and immediately unlock each object to verify
    it's not locked. This is useful before bulk operations like activation.
    
    Args:
        http_request_parameters: HTTP request parameters
        objects: List of dicts with 'uri' and 'name' keys for each object
        
    Returns:
        Dictionary with:
        - 'lockable': List of object names that are not locked
        - 'locked': List of object names that are currently locked
        - 'errors': Dict of object names to error messages
        
    Example:
        >>> status = check_objects_lockable(params, [
        ...     {'uri': '/sap/bc/adt/oo/classes/zcl_test', 'name': 'ZCL_TEST'}
        ... ])
        >>> if status['locked']:
        ...     print(f"Locked objects: {status['locked']}")
    """
    lockable = []
    locked = []
    errors = {}
    
    for obj in objects:
        uri = obj.get('uri', '')
        name = obj.get('name', '')
        
        if not uri or not name:
            continue
            
        try:
            # Try to lock the object
            lock_result = lock(http_request_parameters, uri)
            lock_handle = lock_result.get('LOCK_HANDLE', '')
            
            # If successful, immediately unlock it
            if lock_handle:
                try:
                    unlock(http_request_parameters, uri, lock_handle)
                    lockable.append(name)
                except Exception as unlock_err:
                    # Even if unlock fails, the object was lockable
                    lockable.append(name)
                    errors[name] = f"Warning: Failed to unlock after check: {str(unlock_err)}"
            else:
                locked.append(name)
                errors[name] = "No lock handle returned"
                
        except Exception as e:
            error_msg = str(e)
            # Check if it's a lock conflict
            if "locked" in error_msg.lower() or "being edited" in error_msg.lower() or "409" in error_msg:
                locked.append(name)
                errors[name] = error_msg
            else:
                # Other errors (permissions, not found, etc.)
                errors[name] = error_msg
    
    return {
        'lockable': lockable,
        'locked': locked,
        'errors': errors
    }
