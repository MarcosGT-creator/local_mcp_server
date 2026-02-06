"""
DDIC (Data Dictionary) tools for SAP ADT.
Includes metadata retrieval and data preview for tables and CDS views.
"""

import logging
from typing import Literal
from pydantic import Field
from fastmcp.tools import tool as _tool
from typing import Callable, Any
tool: Callable[..., Any] = _tool  # type: ignore[assignment]

from ._helpers import get_adt_client_safe

logger = logging.getLogger(__name__)

# Type alias for DDIC object types
DDIC_OBJECT_TYPES = Literal["cds", "ddic"]


@tool
def get_ddic_object_metadata(
    object_name: str = Field(
        ...,
        description="Name of the CDS view or transparent table. Examples: 'ZI_CUSTOMER_VIEW', 'MARA' (material master), 'ZCDS_I_PRODUCTS', 'ZC_SERVICE'",
    ),
    object_type: DDIC_OBJECT_TYPES = Field(
        "cds",
        description="Type of object: 'cds' for CDS Views/Data Definitions, 'ddic' for transparent database tables. Use search_object() first to verify object type.",
    ),
) -> str:
    """
    Get metadata or schema for CDS Views or Transparent Tables from SAP system.

    **IMPORTANT:** This tool uses the data preview endpoint which ONLY works for:
    - **CDS Views** (object_type="cds")
    - **Transparent Tables** (object_type="ddic")

    **Call `search_object` first to:**
    - Verify the object exists and is the correct type
    - Confirm it's a CDS view or transparent table (not a structure, domain, etc.)

    **This tool does NOT work for:**
    - DDIC Structures - use `get_object_source` instead
    - Table Types
    - Data Elements
    - Domains
    - Database Views (non-CDS)
    - Lock Objects

    This tool retrieves comprehensive metadata used for data preview functionality in Eclipse ADT.

    The metadata includes detailed column information such as:
    - **name**: Column name (e.g., "MATNR", "OBJECTTYPE")
    - **camelCaseName**: Camel case version (e.g., "Material", "ObjectType")
    - **type**: ABAP data type (e.g., "C" for character, "P" for packed number, "g" for string)
    - **description**: Business description of the column
    - **keyAttribute**: Whether column is part of the primary key (true/false)
    - **colType**: Column type (CHAR, DEC, STRG, INT1, etc.)
    - **isKeyFigure**: Whether it's a key figure for analytical purposes (true/false)
    - **length**: Column length (for character/string types)

    **Supported Object Types:**
    - **cds**: CDS Views (Core Data Services views)
    - **ddic**: Transparent Tables (e.g., MARA, KNA1, VBAK) - default

    **Prerequisites:**
    - Must call `connect_to_sap` first to establish connection
    - Recommended: Call `search_object` to verify object type

    **Args:**
        object_name: Name of the CDS view or transparent table (e.g., "ZI_HEADCUST", "MARA")
        object_type: Type of object - "cds" for CDS Views or "ddic" for transparent tables (default: "ddic")

    **Returns:**
        String containing the metadata XML with detailed column definitions
    """
    adt_client = get_adt_client_safe()
    if isinstance(adt_client, str):
        return adt_client  # Error message

    if not object_name:
        return "Error: Object name is required"

    # Simple label for display
    object_type_label = "CDS View" if object_type == "cds" else "Table"

    try:
        # Use ADT client's generic DDIC metadata method (reuses session and credentials)
        metadata_xml = adt_client.get_ddic_object_metadata(
            object_name=object_name,
            object_type=object_type,
        )

        logger.info(
            f"{object_type_label} metadata retrieved successfully",
            extra={
                "object_name": object_name,
                "object_type": object_type,
                "xml_length": len(metadata_xml) if metadata_xml else 0,
            },
        )

        if len(metadata_xml) == 0:
            return "No data found. You may be connected to dev client (110/310). Use connect_to_sap to switch to test client (120/320) to access data."

        return metadata_xml

    except Exception as e:
        error_msg = str(e)
        logger.error(
            f"Error retrieving {object_type_label} metadata",
            extra={
                "object_name": object_name,
                "object_type": object_type,
                "error_type": type(e).__name__,
                "error": error_msg,
            },
        )
        # Return error message instead of raising to keep it consistent with other tools
        return f"Failed to get metadata: {error_msg}. Try calling `search_object` first to get the correct object type."


@tool
def preview_ddic_data(
    object_name: str = Field(
        ...,
        description="Name of the table or CDS view to query. Examples: 'MARA', 'KNA1', 'VBAK', 'ZI_CUSTOMER_VIEW', 'ZT_CONFIG_TABLE'",
    ),
    sql_query: str = Field(
        ...,
        description="SQL SELECT statement to execute. Examples: 'SELECT * FROM MARA WHERE MTART = \"FERT\"', 'SELECT MATNR, MAKTX FROM MARA', 'SELECT TOP 10 * FROM KNA1 WHERE LAND1 = \"US\"'",
    ),
    row_number: int = Field(
        50,
        description="Maximum number of rows to return. Range: 1-1000. Use smaller values (10-50) for initial exploration, larger for data analysis.",
        ge=1,
        le=1000,
    ),
) -> str:
    """
    Execute a SQL query and retrieve data preview for a DDIC object (table or CDS view).

    This tool executes SQL queries against SAP database tables or CDS views and returns
    the result set with column metadata. Useful for data analysis, testing, and exploration.
    
    **IMPORTANT:** Before using this tool:
    - Call `search_object` to verify the object exists and is a table or CDS view
    - Call `get_ddic_object_metadata` to understand the table structure and column names

    **Supported Objects:**
    - Database Tables (transparent tables) - e.g., MARA, KNA1, VBAK
    - CDS Views (Core Data Services) - e.g., ZI_HEADCUST, C_SALESORDER

    **Not Supported:**
    - DDIC Structures (no data to query)
    - Table Types
    - Data Elements
    - Domains

    **Args:**
        object_name: Name of the table or CDS view to query (e.g., "MARA", "ZDT_SD_RULE", "ZI_HEADCUST")
        sql_query: SQL SELECT statement to execute (e.g., "SELECT * FROM MARA WHERE MTART = 'ZMAT'")
        row_number: Maximum number of rows to return (default: 100, range: 1-1000)

    **Returns:**
        String containing XML response with:
        - totalRows: Total number of rows returned
        - queryExecutionTime: Query execution time in seconds
        - Column metadata for each column:
          * name: Column name
          * type: ABAP data type (C=character, N=numeric, P=packed, etc.)
          * description: Column description
          * keyAttribute: Whether it's a key field
          * colType: Column type (CHAR, CLNT, NUMC, etc.)
          * length: Column length
        - Data organized by columns (each column has a dataSet with all values)

    **Examples:**
        >>> # Connect and get metadata first
        >>> connect_to_sap("https://sap.example.com", "user", "pass", "110")
        >>> metadata = get_ddic_object_metadata("ZDT_SD_RULE", "ddic")
        >>>
        >>> # Preview all columns with row limit
        >>> sql = "SELECT * FROM ZDT_SD_RULE"
        >>> data = preview_ddic_data("ZDT_SD_RULE", sql, row_number=50)
        >>>
        >>> # Preview specific columns with filter
        >>> sql = "SELECT MATNR, MAKTX, MTART FROM MARA WHERE MTART = 'ZMAT'"
        >>> data = preview_ddic_data("MARA", sql, row_number=100)
        >>>
        >>> # Preview with multiple conditions
        >>> sql = '''SELECT MANDT, PROG, DATA, BUKRS, SEQ
        ...          FROM ZDT_SD_RULE
        ...          WHERE PROG = 'CUSTOMER_CREATE' AND BUKRS = 'US00' '''
        >>> data = preview_ddic_data("ZDT_SD_RULE", sql, row_number=200)
    """
    adt_client = get_adt_client_safe()
    if isinstance(adt_client, str):
        return adt_client  # Error message

    if not object_name:
        return "Error: Object name is required"

    if not sql_query:
        return "Error: SQL query is required"

    # Validate row_number range
    if row_number < 1 or row_number > 1000:
        return "Error: row_number must be between 1 and 1000"

    try:
        # Use ADT client's data preview method (reuses session and credentials)
        data_xml = adt_client.preview_ddic_data(
            object_name=object_name,
            sql_query=sql_query,
            row_number=row_number,
        )

        logger.info(
            "Data preview successful",
            extra={
                "object_name": object_name,
                "xml_length": len(data_xml) if data_xml else 0,
            },
        )

        if len(data_xml) == 0:
            return "No data found. You may be connected to dev client (110/310). Use connect_to_sap to switch to test client (120/320) to access data."

        return data_xml

    except Exception as e:
        error_msg = str(e)
        logger.error(
            "Error executing data preview query",
            extra={
                "object_name": object_name,
                "error_type": type(e).__name__,
                "error": error_msg,
            },
        )
        return f"Failed to preview data: {error_msg}. Ensure the object exists and is a table or CDS view. Try calling `search_object` and `get_ddic_object_metadata` first."
