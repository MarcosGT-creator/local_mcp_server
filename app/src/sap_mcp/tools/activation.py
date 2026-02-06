"""
SAP Object Activation Tools

Tools for activating SAP objects after modifications.
"""

from typing import Dict, List
from pydantic import Field
from fastmcp.tools import tool as _tool
from typing import Callable, Any
tool: Callable[..., Any] = _tool  # type: ignore[assignment]

from ._helpers import get_adt_client_safe


@tool
def activate_object(
    object_name: str = Field(
        ...,
        description="Name of the object to activate. Example: 'ZCL_CUSTOMER_API'",
    ),
    object_uri: str = Field(
        ...,
        description="URI of the object (from search_object). Example: '/sap/bc/adt/oo/classes/zcl_customer_api'",
    ),
) -> str:
    """
    Activate an SAP object after modifications.

    Args:
        object_name: Name of the object
        object_uri: URI of the object

    Returns:
        Success or error message
    """
    try:
        adt_client = get_adt_client_safe()
    except Exception as e:
        return f"Error: {str(e)}"

    try:
        adt_client.activate(object_name, object_uri)
        return f"Object '{object_name}' activated successfully"
    except Exception as e:
        return f"Activation Failed: {str(e)}"


@tool
def get_inactive_objects() -> list:
    """
    Get list of inactive objects for the current user.
    
    This tool retrieves all objects that have been modified but not yet activated.
    Useful for:
    - Checking what objects need activation before transport
    - Bulk activation workflows
    - Cleanup of inactive objects
    
    **Returns:**
        List of inactive objects, each containing:
        - uri: Object URI (use with activate_object or activate_multiple_objects)
        - type: Object type (e.g., "CLAS/OC", "DDLS/DF")
        - name: Object name (e.g., "ZCL_MY_CLASS")
        - user: User who last modified the object
        - deleted: Whether the object is marked for deletion
        - transport: Transport request info (if assigned)
    
    **Examples:**
        >>> # Get all inactive objects
        >>> inactive = get_inactive_objects()
        >>> for obj in inactive:
        ...     print(f"{obj['name']} ({obj['type']}) - {obj['uri']}")
    """
    try:
        adt_client = get_adt_client_safe()
    except Exception as e:
        return [{"error": str(e)}]

    try:
        inactive_objects = adt_client.get_inactive_objects()
        return inactive_objects if inactive_objects else [{"message": "No inactive objects found"}]
    except Exception as e:
        return [{"error": f"Failed to get inactive objects: {str(e)}"}]


@tool
def activate_multiple_objects(
    objects: List[Dict[str, str]] = Field(
        ...,
        description="List of objects to activate. Each object must have 'uri' and 'name' keys. Get URIs from search_object() or get_inactive_objects().",
    ),
    preaudit_requested: bool = Field(
        False,
        description="Whether to request pre-activation audit check (default: False). Set to True for stricter validation.",
    ),
    max_poll_attempts: int = Field(
        30,
        description="Maximum number of polling attempts to wait for activation completion (default: 30). Each attempt waits 2 seconds.",
        ge=1,
        le=90,
    ),
) -> str:
    """
    Activate multiple SAP objects in a single activation run.
    
    This tool uses the SAP background activation job API to activate multiple objects
    efficiently. The activation runs asynchronously and the tool polls for completion.
    
    **Advantages over single-object activation:**
    - Faster for multiple objects (single activation run)
    - Resolves dependencies between objects automatically
    - Provides progress tracking
    - Better for bulk activation workflows
    
    **Examples:**
        >>> # Activate specific objects by URI and name
        >>> activate_multiple_objects([
        ...     {'uri': '/sap/bc/adt/ddic/ddl/sources/zc_subs_model', 'name': 'ZC_SUBS_MODEL'},
        ...     {'uri': '/sap/bc/adt/ddic/ddl/sources/zi_serv_i', 'name': 'ZI_SERV_I'}
        ... ])
        
        >>> # Activate all inactive objects
        >>> inactive = get_inactive_objects()
        >>> objects_to_activate = [
        ...     {'uri': obj['uri'], 'name': obj['name']}
        ...     for obj in inactive
        ...     if obj['name']  # Skip entries without names
        ... ]
        >>> activate_multiple_objects(objects_to_activate)
    
    **Returns:**
        Success message with activation details or error message
    """
    try:
        adt_client = get_adt_client_safe()
    except Exception as e:
        return f"Error: {str(e)}"

    # Validate input
    if not objects or len(objects) == 0:
        return "Error: No objects provided for activation"
    
    # Validate each object has required keys
    for i, obj in enumerate(objects):
        if not isinstance(obj, dict):
            return f"Error: Object at index {i} is not a dictionary"
        if 'uri' not in obj or 'name' not in obj:
            return f"Error: Object at index {i} missing 'uri' or 'name' key. Got keys: {list(obj.keys())}"
        if not obj['uri'] or not obj['name']:
            return f"Error: Object at index {i} has empty 'uri' or 'name'"

    try:
        result = adt_client.activate_multiple_objects(
            objects=objects,
            preaudit_requested=preaudit_requested,
            max_poll_attempts=max_poll_attempts,
            poll_interval=2
        )
        
        # Format the result
        status = result.get('status', 'unknown')
        progress = result.get('progress', '0')
        run_id = result.get('run_id', 'N/A')
        objects_count = result.get('objects_count', len(objects))
        
        success_msg = f"✅ Successfully activated {objects_count} object(s)\n\n"
        success_msg += f"Status: {status}\n"
        success_msg += f"Progress: {progress}%\n"
        success_msg += f"Run ID: {run_id}\n"
        
        # Add result details if available
        result_kind = result.get('result_kind', '')
        if result_kind:
            success_msg += f"Result: {result_kind}\n"
        
        # List activated objects
        if objects_count <= 10:
            success_msg += f"\nActivated objects:\n"
            for obj in objects:
                success_msg += f"  - {obj['name']}\n"
        else:
            success_msg += f"\nActivated {objects_count} objects (list truncated)\n"
        
        return success_msg
        
    except Exception as e:
        error_msg = str(e)
        return f"❌ Activation failed: {error_msg}\n\nTip: Check that all objects are inactive and you have activation rights."
