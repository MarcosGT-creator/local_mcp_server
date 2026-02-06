"""
Object manipulation tools for SAP ADT.
Includes delete, package change, test class, and unit testing.
"""

from pydantic import Field
from fastmcp.tools import tool as _tool
from typing import Callable, Any
tool: Callable[..., Any] = _tool  # type: ignore[assignment]

from ._helpers import get_adt_client_safe


@tool
def delete_object(
    object_uri: str = Field(
        ...,
        description="URI of the object (e.g., /sap/bc/adt/oo/classes/zcl_my_class)"
    ),
    lock_handle: str = Field(
        ...,
        description="Lock handle from lock_object"
    ),
) -> str:
    """
    Delete an SAP object.

    **Prerequisites:**
    - Object must be locked first using lock_object()
    - Object must not have dependent objects

    **Args:**
        object_uri: URI of the object
        lock_handle: Lock handle from lock_object

    **Returns:**
        Success or error message
    """
    adt_client = get_adt_client_safe()
    if isinstance(adt_client, str):
        return adt_client  # Error message

    try:
        adt_client.delete(object_uri, lock_handle)
        return "Object deleted successfully"
    except Exception as e:
        return f"Failed to delete object: {str(e)}"


@tool
def change_package(
    object_uri: str = Field(
        ...,
        description="URI of the object (from search_object). Examples: '/sap/bc/adt/ddic/ddl/sources/zce_major_lines', '/sap/bc/adt/oo/classes/zcl_api'"
    ),
    object_name: str = Field(
        ...,
        description="Name of the object. Examples: 'ZCE_MAJOR_LINES', 'ZCL_CUSTOMER_API'"
    ),
    object_type: str = Field(
        ...,
        description="Type of object (from search_object). Examples: 'DDLS/DF', 'CLAS/OC', 'PROG/P'"
    ),
    old_package: str = Field(
        ...,
        description="Current package name. Examples: '$TMP', 'ZOLD_PACKAGE'"
    ),
    new_package: str = Field(
        ...,
        description="Target package name. Examples: 'ZGET_SUBS_API_V2', 'ZSD_MASTER_DATA'"
    ),
    transport_number: str = Field(
        ...,
        description="Transport request number (parent TR, not child task). Examples: 'DHAK905086', 'D2AK904114'"
    ),
) -> str:
    """
    Change the package assignment of an SAP object and assign it to a transport.
    
    This tool moves objects between packages (typically from $TMP to transportable packages)
    and assigns them to a transport request in a single operation.
    
    **Use Cases:**
    - Move objects from $TMP (local) to transportable packages
    - Reassign objects to different packages during refactoring
    - Consolidate objects from multiple packages
    
    **Prerequisites:**
    - Object must exist and be accessible
    - User must have authorization for both old and new packages
    - Transport request must exist and be modifiable
    - Object must not be locked
    
    **Workflow:**
    The tool executes a 3-step refactoring flow:
    1. **Evaluate** - Check if package change is possible
    2. **Preview** - Preview the changes with new package and transport
    3. **Execute** - Perform the package change
    
    **Examples:**
        >>> # Move CDS view from $TMP to transportable package
        >>> change_package(
        ...     object_uri="/sap/bc/adt/ddic/ddl/sources/zce_major_lines",
        ...     object_name="ZCE_MAJOR_LINES",
        ...     object_type="DDLS/DF",
        ...     old_package="$TMP",
        ...     new_package="ZGET_SUBS_API_V2",
        ...     transport_number="DHAK905086"
        ... )
        
        >>> # Move class to different package
        >>> change_package(
        ...     object_uri="/sap/bc/adt/oo/classes/zcl_helper",
        ...     object_name="ZCL_HELPER",
        ...     object_type="CLAS/OC",
        ...     old_package="$TMP",
        ...     new_package="ZSD_UTILITIES",
        ...     transport_number="D2AK904120"
        ... )
    
    **Returns:**
        Success message with package change details, or error message if change fails
    
    **Important Notes:**
    - Use the **parent transport request** number, not the child task
    - Object will be automatically assigned to your active child task within the transport
    - After package change, object remains inactive - activate it separately
    - Package change cannot be undone automatically - requires manual reversal
    
    **Common Issues:**
    - "Object is locked" - Unlock the object first
    - "No authorization" - Check package change authorization
    - "Transport is released" - Use a modifiable transport request
    - "Package does not exist" - Verify target package name
    """
    adt_client = get_adt_client_safe()
    if isinstance(adt_client, str):
        return adt_client  # Error message

    try:
        result = adt_client.change_package(
            object_uri=object_uri,
            object_name=object_name,
            object_type=object_type,
            old_package=old_package,
            new_package=new_package,
            transport_number=transport_number
        )
        
        success_msg = f"✅ Package changed successfully\n\n"
        success_msg += f"Object: {result['object_name']}\n"
        success_msg += f"Old Package: {result['old_package']}\n"
        success_msg += f"New Package: {result['new_package']}\n"
        success_msg += f"Transport: {result['transport']}\n\n"
        success_msg += f"💡 Next Steps:\n"
        success_msg += f"  - Object is now in {result['new_package']} package\n"
        success_msg += f"  - Object remains inactive - use activate_object() to activate\n"
        success_msg += f"  - Changes are assigned to transport {result['transport']}"
        
        return success_msg
        
    except Exception as e:
        error_msg = str(e)
        return f"❌ Package change failed: {error_msg}\n\nTip: Ensure object is not locked and you have authorization for both packages."


@tool
def create_test_class_include(
    class_name: str = Field(
        ...,
        description="Name of the ABAP class (e.g., ZCL_MY_CLASS)"
    ),
    lock_handle: str = Field(
        ...,
        description="Lock handle from lock_object"
    ),
) -> str:
    """
    Create a test class include for a given ABAP class.

    **Prerequisites:**
    - Class must be locked first using lock_object()
    - Class must not already have a test class include

    **Args:**
        class_name: Name of the ABAP class (e.g., ZCL_MY_CLASS)
        lock_handle: Lock handle from lock_sap_object

    **Returns:**
        Success or error message
    """
    adt_client = get_adt_client_safe()
    if isinstance(adt_client, str):
        return adt_client  # Error message

    try:
        result = adt_client.create_test_class_include(class_name, lock_handle)
        if result:
            return f"Test class include created for {class_name}."
        else:
            return f"Failed to create test class include for {class_name}."
    except Exception as e:
        return f"Error: {str(e)}"


@tool
def run_unit_test(
    object_uri: str = Field(
        ...,
        description="URI of the object (e.g., /sap/bc/adt/oo/classes/zcl_my_class)"
    ),
) -> str:
    """
    Run ABAP unit tests for a given object.
    
    Returns data in XML format. If possible convert to structured data to present better.

    **Args:**
        object_uri: URI of the object (e.g., /sap/bc/adt/oo/classes/zcl_my_class)

    **Returns:**
        List of test results (alerts) in XML format
    """
    adt_client = get_adt_client_safe()
    if isinstance(adt_client, str):
        return adt_client  # Error message

    try:
        results = adt_client.run_unit_test(object_uri)
        return str(results)
    except Exception as e:
        return f"Error: {str(e)}"


@tool
def create_object(
    object_type: str = Field(
        ...,
        description="Type of object to create. Examples: 'CLAS/OC' (ABAP Class), 'PROG/P' (Program), 'DDLS/DF' (CDS View), 'TABL/DT' (Table), 'FUGR/F' (Function Group). Use get_creatable_object_types() for full list.",
    ),
    name: str = Field(
        ...,
        description="Object name following SAP naming conventions. Examples: 'ZCL_MY_CLASS', 'ZR_CUSTOMER_REPORT', 'ZI_CUSTOMER_VIEW'. Must start with Z for custom objects.",
    ),
    package: str = Field(
        ...,
        description="SAP Package. Use '$TMP' for local development objects, or provide existing package like 'ZPACKAGE'",
    ),
    description: str = Field(
        ...,
        description="Business description of the object. Examples: 'Customer Master Data API', 'Sales Order Processing Class', 'Material Master CDS View'.",
    ),
    corr_nr: str = Field(
        "",
        description="Transport request number (required for custom packages, optional for $TMP). Example: 'DHAK905086'",
    ),
) -> str:
    """
    Create a new SAP object using ADT endpoints.

    This tool creates various types of SAP development objects like classes, programs,
    CDS views, tables, etc. The object is created in the specified package and can be
    modified immediately after creation.

    **Prerequisites:**
    - Must have developer access to the target package
    - Package must exist (except for $TMP which is always available)
    - Object name must follow SAP naming conventions

    **Naming Conventions:**
    - Custom objects must start with 'Z' or 'Y'
    - Classes: ZCL_* (e.g., ZCL_CUSTOMER_API)
    - Interfaces: ZIF_* (e.g., ZIF_ORDER_PROCESSING)
    - Programs: ZR_* (e.g., ZR_SALES_REPORT)
    - CDS Views: ZI_*, ZC_* (e.g., ZI_CUSTOMER_VIEW)
    - Tables: ZDT_* (e.g., ZDT_CUSTOMER_CONFIG)

    **Common Object Types:**
    - **CLAS/OC**: ABAP Classes (business logic, APIs)
    - **PROG/P**: ABAP Programs (reports, batch jobs)
    - **DDLS/DF**: CDS Views (data modeling, analytics)
    - **TABL/DT**: Database Tables (master/transaction data)
    - **FUGR/F**: Function Groups (reusable functions)
    - **INTF/OI**: Interfaces (contracts, polymorphism)

    **Examples:**
        >>> # Create a customer API class
        >>> create_object(
        ...     object_type="CLAS/OC",
        ...     name="ZCL_CUSTOMER_API",
        ...     package="ZSD_MASTER_DATA",
        ...     description="Customer Master Data API for external integration"
        ... )

        >>> # Create local development object
        >>> create_object(
        ...     object_type="CLAS/OC",
        ...     name="ZCL_TEST_HELPER",
        ...     package="$TMP",
        ...     description="Test Helper Class for Development"
        ... )

    **Returns:**
        Success message with object details, or error message if creation fails

    **Next Steps After Creation:**
    1. Use `search_object()` to get the object URI
    2. Use `lock_object()` to lock for editing
    3. Use `set_object_source()` to add code/definition
    4. Use `unlock_object()` and `activate_object()` to complete
    """
    from src.abap_adt_client.api.create import CREATEABLE_TYPES
    
    adt_client = get_adt_client_safe()
    if isinstance(adt_client, str):
        return adt_client  # Error message

    if object_type not in CREATEABLE_TYPES:
        available = ", ".join(CREATEABLE_TYPES.keys())
        return f"Error: Invalid object type '{object_type}'. Available types: {available}"

    try:
        adt_client.create(object_type, name, package, description, corr_nr)
        return f"Successfully created {object_type} object '{name}' in package '{package}'"
    except Exception as e:
        return f"Failed to create object: {str(e)}"


@tool
def get_creatable_object_types() -> dict:
    """
    Get list of all SAP object types that can be created via ADT.
    
    **Returns:**
        Dictionary of creatable object types with their paths and XML names.
        
    **Example:**
        >>> types = get_creatable_object_types()
        >>> for obj_type, details in types.items():
        ...     print(f"{obj_type}: {details['path']}")
    """
    from src.abap_adt_client.api.create import CREATEABLE_TYPES
    
    result = {}
    for obj_type, details in CREATEABLE_TYPES.items():
        result[obj_type] = {
            "path": details["path"],
            "xml_name": details["xml_name"],
        }
    return result
