"""
Transport management tools for SAP ADT.
Includes transport creation, listing, and object management.
"""

from typing import Optional, List, Dict, Any, Literal
from pydantic import Field
from fastmcp.tools import tool as _tool
from typing import Callable, Any
tool: Callable[..., Any] = _tool  # type: ignore[assignment]

from ._helpers import get_adt_client_safe


@tool
def transport_check(
    object_uri: str = Field(
        ...,
        description="URI of the object to check (e.g., /sap/bc/adt/oo/classes/zcl_test/source/main)"
    ),
) -> Any:
    """
    Perform a transport check for an SAP object.

    Returns structured data with available transport requests and object metadata.
    This is used when an object is NOT yet locked in a transport. The returned
    list of transport requests allows the user to select which transport
    to use for the object modification.

    **Returns:**
        Dictionary with object metadata and list of available transport requests:
        - PGMID: Program ID
        - OBJECT: Object type
        - OBJECTNAME: Object name
        - DEVCLASS: Development class/package
        - REQUESTS: List of transport requests with TRKORR, AS4TEXT, AS4USER, etc.

    **Example:**
        >>> result = transport_check("/sap/bc/adt/oo/classes/zcl_test/source/main")
        >>> print(f"Package: {result['DEVCLASS']}")
        >>> for req in result['REQUESTS']:
        ...     print(f"{req['TRKORR']}: {req['AS4TEXT']}")
    """
    adt_client = get_adt_client_safe()
    if isinstance(adt_client, str):
        return adt_client  # Error message

    try:
        result = adt_client.transport_check(object_uri)
        return result
    except Exception as e:
        return f"Error: {str(e)}"


@tool
def create_transport_and_assign(
    devclass: str = Field(
        ..., description="Development class/package (e.g., ZSAP_LLM_API)"
    ),
    request_text: str = Field(
        ..., description="Description for the transport (e.g., 'Bug fix for API')"
    ),
    ref: str = Field(
        ...,
        description="Reference URI of the object (e.g., /sap/bc/adt/oo/classes/zcl_test/source/main)",
    ),
    operation: str = Field("", description="Operation type (optional, usually empty)"),
) -> Any:
    """
    Create a new transport request and assign an object to it.

    Creates a new workbench transport request for transporting object
    modifications. This is typically called after transport_check() when
    the user wants to create a new transport instead of using an existing one.

    **Returns:**
        Dictionary with the new TRKORR (transport number) and any messages:
        - TRKORR: Transport request number (e.g., "D2AK904083")
        - MESSAGES: List of any messages from the system

    **Example:**
        >>> result = create_transport_and_assign(
        ...     devclass="ZSAP_LLM_API",
        ...     request_text="Fix bug in API class",
        ...     ref="/sap/bc/adt/oo/classes/zcl_api/source/main"
        ... )
        >>> print(f"Created transport: {result['TRKORR']}")
    """
    adt_client = get_adt_client_safe()
    if isinstance(adt_client, str):
        return adt_client  # Error message

    try:
        result = adt_client.create_transport_and_assign(
            devclass, request_text, ref, operation
        )
        return result
    except Exception as e:
        return f"Error: {str(e)}"


@tool
def create_transport_organizer(
    description: str = Field(
        ..., description="Description of the transport request (e.g., 'Bug fixes for API', 'Feature implementation')"
    ),
    target: str = Field(
        "", description="Target system (default: '', or ask user)"
    ),
    tr_type: Literal["K", "W"] = Field(
        "K", description="Transport type: 'K' for Workbench (default), 'W' for Customizing"
    ),
    owner: str = Field(
        "", description="Task owner username (optional, defaults to current user)"
    ),
) -> Any:
    """
    Create a new transport request via Transport Organizer (standalone).

    This creates a standalone transport request that is NOT tied to a specific object.
    Use this when you want to create an empty transport that can be used later for
    multiple objects, or when creating a transport from the Transport Organizer view.

    This is simpler than create_transport_and_assign() which requires an object reference.

    **Args:**
        description: Description of the transport request (e.g., "Bug fixes for SAP API")
        target: Target system (default: "", use "/ZNQUALIT/" for quality, "/ZPRD/" for production)
        tr_type: "K" for Workbench (default), "W" for Customizing
        owner: Task owner (optional, defaults to current user)

    **Returns:**
        TransportOrganizerResult with:
        - TRKORR: Transport request number (e.g., "DHAK905087")
        - DESCRIPTION: Transport description
        - TYPE: Transport type (K or W)
        - TARGET: Target system
        - TARGET_DESC: Target system description
        - URI: Transport URI in the system
        - TASK_NUMBER: Child task number (e.g., "DHAK905088")
        - TASK_OWNER: Task owner username
        - TASK_URI: Task URI in the system

    **Example:**
        >>> result = create_transport_organizer(
        ...     description="TNC_O2CSM-26858_SOM_W_I001A_TNC+ Late Renewal"
        ... )
        >>> print(f"Created transport: {result['TRKORR']}")

    **Important:**
        SAP automatically creates BOTH a parent transport request AND a child task.
        The parent TRKORR is the transport request, and TASK_NUMBER is the automatically created
        child task assigned to the current user.
        
        **CRITICAL FOR OBJECT ASSIGNMENT:**
        When modifying objects, you must use the **TASK_NUMBER** (child task), NOT the parent TRKORR.
        - For locking: SAP automatically assigns objects to your active task
        - For set_object_source: Use corr_nr from lock_object result (which will be the child task)
        - Objects are always assigned to tasks, not to the parent transport request directly
    """
    adt_client = get_adt_client_safe()
    if isinstance(adt_client, str):
        return adt_client  # Error message

    try:
        result = adt_client.create_transport_organizer(
            description, target, tr_type, owner
        )
        return result
    except Exception as e:
        return f"Error: {str(e)}"


@tool
def list_transports(
    targets: bool = True,
    transport_number: Optional[str] = None
) -> Any:
    """
    List transport requests from SAP system.

    Fetches transport requests from the SAP Transport Organizer based on the user's
    saved configuration in Eclipse ADT. The results are filtered according to the
    settings stored in that configuration (user, status, transport type, etc.).

    **Args:**
        targets: Include target system information (default: True)
        transport_number: Optional transport number to filter by (e.g., 'D2AK904114').
                         Useful for checking released transports or searching with wildcards.
                         Can include wildcards (*) for pattern matching (e.g., 'D2AK9041*').

    **Returns:**
        Dictionary with list of transport requests and total count:
        - TRANSPORTS: List of transport info dictionaries with:
            - TRKORR: Transport request number
            - DESCRIPTION: Transport description
            - TYPE: K=Workbench, W=Customizing
            - STATUS: D=Modifiable, R=Released
            - OWNER: Owner username
            - TARGET: Target system
            - CREATED_DATE: Creation date
            - CREATED_TIME: Creation time
            - URI: Transport URI
        - TOTAL_COUNT: Total number of transports found

    **Example:**
        >>> result = list_transports()
        >>> print(f"Found {result['TOTAL_COUNT']} transports")
        >>> for tr in result['TRANSPORTS']:
        ...     print(f"{tr['TRKORR']}: {tr['DESCRIPTION']}")
        ...     print(f"  Owner: {tr['OWNER']} | Status: {tr['STATUS']}")
        
        >>> # Check specific transport (including released ones)
        >>> result = list_transports(transport_number='D2AK904114')
        
        >>> # Search with pattern
        >>> result = list_transports(transport_number='D2AK9041*')

    **Note:**
        The filters (user, status, transport type) come from your saved configuration
        in Eclipse ADT's Transport Organizer. To change filters, modify your
        configuration in Eclipse ADT.
    """
    adt_client = get_adt_client_safe()
    if isinstance(adt_client, str):
        return {"error": adt_client, "TRANSPORTS": [], "TOTAL_COUNT": 0}

    try:
        result = adt_client.list_transports(targets, transport_number)
        return result
    except Exception as e:
        return {"error": str(e), "TRANSPORTS": [], "TOTAL_COUNT": 0}


@tool
def get_transport_objects(
    transport_number: str = Field(
        ...,
        description="Transport request or task number (e.g., 'DHAK905111', 'DHAK905112'). Can be parent TR or child task."
    ),
) -> List[Dict[str, Any]]:
    """
    Get list of all objects in a transport request or task.
    
    **Important: Parent TR vs Child Task:**
    - If child tasks are NOT released: Objects are in the child tasks, not the parent TR
    - If child tasks are released: Objects are moved to the parent TR
    - This tool automatically retrieves objects from wherever they are (parent or tasks)
    
    **Use Cases:**
    - View all objects before releasing transport
    - Verify which objects are assigned to a transport
    - Audit transport contents before deployment
    - Check if specific objects are in a transport
    
    **Examples:**
        >>> # Get objects from parent TR (works if tasks are released)
        >>> objects = get_transport_objects("DHAK905110")
        >>> for obj in objects:
        ...     print(f"{obj['TYPE']}: {obj['NAME']} - {obj['OBJ_DESC']}")
        
        >>> # Get objects from child task (works if task not released)
        >>> objects = get_transport_objects("DHAK905111")
        >>> print(f"Found {len(objects)} objects in task")
        
        >>> # Filter by object type
        >>> objects = get_transport_objects("DHAK905110")
        >>> methods = [obj for obj in objects if obj['TYPE'] == 'METH']
        >>> classes = [obj for obj in objects if obj['TYPE'] == 'CLAS']
    
    **Returns:**
        List of object dictionaries, each containing:
        - **PGMID**: Program ID (e.g., 'LIMU', 'R3TR')
        - **TYPE**: Object type (e.g., 'CLAS', 'METH', 'DDLS', 'TABL')
        - **NAME**: Object name (preserves exact spacing for methods)
        - **OBJ_DESC**: Object description
        - **POSITION**: Position in transport
        - **LOCK_STATUS**: Lock status
        - **IMG_ACTIVITY**: IMG activity
    """
    adt_client = get_adt_client_safe()
    if isinstance(adt_client, str):
        return [{"error": adt_client}]
    
    try:
        objects = adt_client.get_transport_objects(transport_number)
        return objects if objects else []
    except Exception as e:
        return [{"error": f"Failed to get transport objects: {str(e)}"}]
