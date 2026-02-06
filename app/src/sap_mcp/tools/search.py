"""
SAP Object Search Tools

Tools for searching and exploring SAP objects, packages, and their contents.
"""

from typing import Optional
from pydantic import Field
from fastmcp.tools import tool as _tool
from typing import Callable, Any
tool: Callable[..., Any] = _tool  # type: ignore[assignment]

from ._helpers import get_adt_client_safe


@tool
def search_object(
    query: str = Field(
        ...,
        description="Search query using object name or wildcard pattern. Examples: 'ZCL_*' (classes starting with ZCL), Z* (any custom object)",
    ),
    max_results: int = Field(
        10,
        description="Maximum number of results to return. Range: 1-100. Use 20-50 for broad searches, 5-10 for specific searches.",
        ge=1,
        le=100,
    ),
    object_type: Optional[str] = Field(
        None,
        description="Optional object type filter (TYPE/SUBTYPE). Examples: 'CLAS/OC' (classes), 'SRVD/SRV' (OData v4 service name), 'SRVB/SVB' (service namespace), 'IWSV/SRV' (OData v2 services), 'DDLS/DF' (CDS views), 'TABL/DT' (tables). Omit to search all types.",
    ),
) -> list:
    """
    Search for SAP objects by name or pattern.

    This tool searches across all SAP object types in the system and returns matching results
    with their URIs needed for further operations (lock, get source, etc.).

    **Common Object Types:**

    **ABAP Development:**
    - CLAS/OC: ABAP Class
    - PROG/P: ABAP Program
    - INTF/OI: ABAP Interface
    - FUGR/F: Function Group
    - FUGR/FF: Function Module
    - PROG/I: Include Program

    **Database & Data Modeling:**
    - TABL/DT: Database Table
    - DTEL/DE: Data Element
    - DOMA/DD: Domain
    - DDLS/DF: CDS View (Data Definition)
    - DDLX/EX: CDS Metadata Extension
    - DCLS/DL: CDS Access Control

    **RAP (RESTful ABAP Programming):**
    - BDEF/BDO: Behavior Definition
    - SRVD/SRV: Service Definition (oData v4)
    - SRVB/SVB: Service Binding (oData v4)

    **Gateway Services (oData v2):**
    - IWSV/SRV: Gateway Service
    - IWMO: Model (Gateway)
    - IWPR: Service Builder Project
    - IWSG: Service Group

    **Examples:**
        # Search for all objects starting with ZSD_PRODUCT
        >>> search_object("ZSD_PRODUCT*")

        # Search only for service definitions
        >>> search_object("Z*API*", object_type="SRVD/SRV")

        # Search for classes containing "HELPER"
        >>> search_object("*HELPER*", object_type="CLAS/OC", max_results=20)

    Returns:
        List of matching objects with their details:
        - name: Object name
        - type: Object type (e.g., SRVD/SRV, CLAS/OC)
        - uri: Object URI (needed for lock, get_source, etc.)
        - packageName: Package containing the object
        - description: Object description
    """
    try:
        adt_client = get_adt_client_safe()
    except Exception as e:
        return [{"error": str(e)}]

    try:
        results = adt_client.search_object(query, max_results, object_type)
        return results if results else [{"message": "No objects found"}]
    except Exception as e:
        return [{"error": str(e)}]


@tool
def get_package_objects(
    package_name: str = Field(
        ...,
        description="Name of the SAP package to explore. Examples: 'ZGET_SUBS_API', '$TMP', 'ZSD_MASTER_DATA'",
    ),
    object_search_pattern: str = Field(
        "*",
        description="Pattern for filtering object names. Use '*' for all objects, or specific patterns like 'Z*CUSTOMER*'",
    ),
    group_filter: Optional[str] = Field(
        None,
        description="Optional group filter. Common values: 'CORE_DATA_SERVICES', 'SOURCE_LIBRARY', 'OTHER', 'TEXT_OBJECTS'. Leave empty to see all groups.",
    ),
    type_filter: Optional[str] = Field(
        None,
        description="Optional type filter. Common values: 'DDLS' (CDS Views), 'CLAS' (Classes), 'PROG' (Programs), 'TABL' (Tables). Leave empty to see all types.",
    ),
) -> list:
    """
    Fetch objects from a package using the virtual folders API.
    
    This tool supports hierarchical exploration of package contents:
    1. **First call** (no filters): Returns top-level groups like CORE_DATA_SERVICES, SOURCE_LIBRARY
    2. **Second call** (with group_filter): Returns object types within that group like DDLS, CLAS, PROG
    3. **Third call** (with group_filter + type_filter): Returns actual objects of that type
    
    **Common Groups:**
    - **CORE_DATA_SERVICES**: CDS Views, Data Definitions, Access Controls
    - **DICTIONARY**: Database Tables, Structures, Data Elements
    - **SOURCE_LIBRARY**: Classes, Programs, Interfaces, Function Groups
    - **OTHER**: Miscellaneous objects
    
    **Usage Examples:**
    
        # Step 1: Get all groups in a package
        >>> get_package_objects(package_name="ZGET_SUBS_API")
        
        # Step 2: Get object types within a group
        >>> get_package_objects(
        ...     package_name="ZGET_SUBS_API",
        ...     group_filter="CORE_DATA_SERVICES"
        ... )
        
        # Step 3: Get all CDS views in the package
        >>> get_package_objects(
        ...     package_name="ZGET_SUBS_API",
        ...     group_filter="CORE_DATA_SERVICES",
        ...     type_filter="DDLS"
        ... )
    
    Returns:
        List of folders or objects from the package
    """
    try:
        adt_client = get_adt_client_safe()
    except Exception as e:
        return [{"error": str(e)}]

    try:
        results = adt_client.get_package_objects(
            package_name, object_search_pattern, group_filter, type_filter
        )
        return results if results else [{"message": "No objects found in package"}]
    except Exception as e:
        return [{"error": str(e)}]
