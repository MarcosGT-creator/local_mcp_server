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
        SAP_CONTEXT_ID: sap-contextid cookie value at lock time (for unlock routing)
    """
    LOCK_HANDLE: str
    CORRNR: str
    CORRUSER: str
    CORRTEXT: str
    IS_LOCAL: str
    IS_LINK_UP: str
    MODIFICATION_SUPPORT: str
    SAP_CONTEXT_ID: str


def lock(http_request_parameters: HttpRequestParameters, object_uri: str) -> LockResult:
    """Lock an SAP object for editing.

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
        import xml.etree.ElementTree as ET
        root = ET.fromstring(response.text)
        data = root.find('.//DATA')

        result: LockResult = {}
        if data is not None:
            result['LOCK_HANDLE'] = data.findtext('LOCK_HANDLE', '')
            result['CORRNR'] = data.findtext('CORRNR', '')
            result['CORRUSER'] = data.findtext('CORRUSER', '')
            result['CORRTEXT'] = data.findtext('CORRTEXT', '')
            result['IS_LOCAL'] = data.findtext('IS_LOCAL', '')
            result['IS_LINK_UP'] = data.findtext('IS_LINK_UP', '')
            result['MODIFICATION_SUPPORT'] = data.findtext('MODIFICATION_SUPPORT', '')

        # Capture sap-contextid from the session cookies AFTER the lock response.
        # SAP uses this cookie for work-process affinity: the unlock MUST be sent
        # with the same contextid that was active when the lock was created.
        context_id = http_request_parameters['session'].cookies.get('sap-contextid', '')
        result['SAP_CONTEXT_ID'] = context_id

        if not result.get('LOCK_HANDLE'):
            raise Exception(f"Failed to extract lock handle from response.\n{response.text}")

        return result
    else:
        raise Exception(
            f"{response.status_code} Failed to lock {object_uri}.\n{response.text}"
        )


def unlock(
    http_request_parameters: HttpRequestParameters,
    object_uri: str,
    lock_handle: str,
    context_id: str = "",
) -> bool:
    """Unlock an SAP object after editing.

    Args:
        http_request_parameters: HTTP request parameters
        object_uri: URI of the object to unlock
        lock_handle: Lock handle obtained from lock()
        context_id: sap-contextid captured at lock time. Required for correct
                    SAP work-process routing (obtained from LockResult['SAP_CONTEXT_ID']).
    """
    from urllib.parse import quote

    # Pass sap-contextid as a per-request cookie (NOT written to session).
    # SAP uses this cookie to route the unlock to the exact work process that
    # holds the lock. Writing it to the session would contaminate subsequent
    # stateless requests and cause ICMENOSESSION errors.
    per_request_cookies = {"sap-contextid": context_id} if context_id else None

    response = request(
        http_request_parameters=http_request_parameters,
        uri=object_uri,
        body=None,
        params={"_action": "UNLOCK", "lockHandle": quote(lock_handle, safe="")},
        method="POST",
        content_type=None,
        accept="*/*",
        cookies=per_request_cookies,
    )
    if response.status_code in (200, 204):
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
            lock_result = lock(http_request_parameters, uri)
            lock_handle = lock_result.get('LOCK_HANDLE', '')

            if lock_handle:
                try:
                    unlock(
                        http_request_parameters, uri, lock_handle,
                        context_id=lock_result.get('SAP_CONTEXT_ID', '')
                    )
                    lockable.append(name)
                except Exception as unlock_err:
                    lockable.append(name)
                    errors[name] = f"Warning: Failed to unlock after check: {str(unlock_err)}"
            else:
                locked.append(name)
                errors[name] = "No lock handle returned"

        except Exception as e:
            error_msg = str(e)
            if "locked" in error_msg.lower() or "being edited" in error_msg.lower() or "409" in error_msg:
                locked.append(name)
                errors[name] = error_msg
            else:
                errors[name] = error_msg

    return {
        'lockable': lockable,
        'locked': locked,
        'errors': errors
    }
