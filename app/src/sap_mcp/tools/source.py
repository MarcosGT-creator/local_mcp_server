"""
SAP Object Source Code Tools

Tools for locking, reading, modifying, and managing SAP object source code.
"""

from typing import Literal
from pydantic import Field
from fastmcp.tools import tool as _tool
from typing import Callable, Any
tool: Callable[..., Any] = _tool  # type: ignore[assignment]

from src.abap_adt_client.api.lock import LockResult
from src.abap_adt_client.api.objectstructure import ClassStructureResult
from ._helpers import get_adt_client_safe


@tool
def lock_object(
    object_uri: str = Field(
        ...,
        description="URI of the SAP object to lock (obtained from search_object). Examples: '/sap/bc/adt/oo/classes/zcl_customer_api', '/sap/bc/adt/programs/programs/z_sales_report'",
    )
) -> str | LockResult:
    """
    Lock an SAP object for editing.

    This must be called before modifying any object source code. The lock prevents
    other users from editing the same object simultaneously.

    **Workflow:**
    1. `search_object()` - Find object and get URI
    2. `lock_object()` - Lock for editing (this function)
    3. `set_object_source()` - Modify the code
    4. `unlock_object()` - Release the lock
    5. `activate_object()` - Activate changes

    **Returns:**
        LockResult object containing:
        - lock_handle: Required for set_object_source() and unlock_object()
        - corr_nr: Transport request number (if assigned)
        - messages: Any system messages
    """
    try:
        adt_client = get_adt_client_safe()
    except Exception as e:
        return f"Error: {str(e)}"

    try:
        return adt_client.lock(object_uri)
    except Exception as e:
        return str(e)


@tool
def unlock_object(object_uri: str, lock_handle: str) -> bool | str:
    """
    Unlock an SAP object after editing.
    If modifications were made, remember to activate the object after unlocking.

    Args:
        object_uri: URI of the object
        lock_handle: Lock handle obtained from lock_object

    Returns:
        Success or error message
    """
    try:
        adt_client = get_adt_client_safe()
    except Exception as e:
        return f"Error: {str(e)}"

    try:
        return adt_client.unlock(object_uri, lock_handle)
    except Exception as e:
        return f"Failed to unlock object: {str(e)}"


@tool
def get_object_source(
    object_uri: str = Field(
        ...,
        description="URI of the object (from search_object). Examples: '/sap/bc/adt/oo/classes/zcl_customer_api', '/sap/bc/adt/ddic/ddl/sources/zcds_view'",
    ),
    version: Literal["active", "inactive"] = Field(
        "active",
        description="Version to retrieve - 'active' (compiled) or 'inactive' (working copy)",
    ),
) -> str:
    """
    Get source code of an SAP object.

    Args:
        object_uri: URI of the object
        version: Version to retrieve - "active" or "inactive" (default: active)

    Returns:
        Source code of the object
    """
    try:
        adt_client = get_adt_client_safe()
    except Exception as e:
        return f"Error: {str(e)}"

    try:
        source = adt_client.get_object_source(object_uri, version)
        return source
    except Exception as e:
        return f"Failed to get source code: {str(e)}"


@tool
def set_object_source(
    object_uri: str = Field(
        ...,
        description="URI of the object to update (from search_object). Examples: '/sap/bc/adt/oo/classes/zcl_customer_api/source/main', '/sap/bc/adt/programs/programs/z_report'",
    ),
    source_code: str = Field(
        ...,
        description="Complete ABAP source code to set. Examples: ABAP class definition with methods, report program code, CDS view definition",
    ),
    lock_handle: str = Field(
        ...,
        description="Lock handle obtained from lock_object(). Required to authorize the modification.",
    ),
    corr_nr: str | None = Field(
        None,
        description="Transport request number (optional). Usually obtained from lock_object result. Used for change tracking.",
    ),
) -> str:
    """
    Update source code of an SAP object.

    This function replaces the entire source code of an object. The object must be
    locked first using lock_object().

    **Complete Workflow:**
    1. `search_object()` - Find object URI
    2. `lock_object()` - Get lock handle
    3. `set_object_source()` - Update code (this function)
    4. `syntax_check()` - Validate syntax (optional but recommended)
    5. `unlock_object()` - Release lock
    6. `activate_object()` - Activate changes

    **Returns:**
        Success message if update completes, or error message if it fails
    """
    try:
        adt_client = get_adt_client_safe()
    except Exception as e:
        return f"Error: {str(e)}"

    try:
        adt_client.set_object_source(object_uri, source_code, lock_handle, corr_nr)
        return "Source code updated successfully"
    except Exception as e:
        return f"Failed to update source code: {str(e)}"


@tool
def get_object_structure(object_uri: str) -> ClassStructureResult | str:
    """
    Get the structure of a SAP object, including sub-components.

    This retrieves the internal structure/hierarchy of an object, such as:
    - Classes: Methods, attributes, types
    - Function groups: Function modules
    - Programs: Includes

    Args:
        object_uri: URI of the object (obtained from search_object)

    Returns:
        Dictionary with object structure or error message
    """
    try:
        adt_client = get_adt_client_safe()
    except Exception as e:
        return f"Error: {str(e)}"

    try:
        structure = adt_client.object_structure(object_uri)
        return structure
    except Exception as e:
        return f"Failed to get object structure: {str(e)}"


@tool
def syntax_check(
    object_uri: str = Field(
        ...,
        description="URI of the object to check syntax. Example: '/sap/bc/adt/oo/classes/zcl_my_class/source/main'",
    ),
    source_code: str = Field(
        ...,
        description="The ABAP source code to check for syntax errors",
    ),
    include_uri: str = Field(
        "",
        description="URI of include (optional, defaults to object_uri)",
    ),
    version: Literal["active", "inactive"] = Field(
        "inactive",
        description="Version to check - 'active' or 'inactive'",
    ),
) -> str:
    """
    Perform syntax check on ABAP source code.

    This validates the syntax of ABAP code before activation.
    Use this after set_object_source() to catch errors early.

    Args:
        object_uri: URI of the object
        source_code: The ABAP source code to validate
        include_uri: URI of include (defaults to object_uri if empty)
        version: Version to check against

    Returns:
        Syntax check results (errors, warnings) or success message
    """
    try:
        adt_client = get_adt_client_safe()
    except Exception as e:
        return f"Error: {str(e)}"

    try:
        inc_uri = include_uri if include_uri else object_uri
        result = adt_client.syntax_check(object_uri, inc_uri, source_code, version)
        if not result:
            return "Syntax check passed - no errors"
        # Format results
        messages = []
        for r in result:
            messages.append(f"{r.get('severity', 'INFO')}: Line {r.get('line', '?')} - {r.get('message', 'Unknown')}")
        return "\n".join(messages) if messages else "Syntax check passed - no errors"
    except Exception as e:
        return f"Syntax check failed: {str(e)}"


@tool
def format_source_code(
    source_code: str = Field(
        ...,
        description="ABAP source code to format"
    ),
) -> str:
    """
    Format ABAP source code using SAP's pretty printer.

    **Args:**
        source_code: ABAP source code to format

    **Returns:**
        Formatted ABAP source code
    """
    try:
        adt_client = get_adt_client_safe()
    except Exception as e:
        return f"Error: {str(e)}"

    try:
        formatted = adt_client.prettyprint(source_code)
        return formatted
    except Exception as e:
        return f"Failed to format source code: {str(e)}"
