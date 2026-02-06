"""
Data Dictionary and CDS metadata API operations using ADT client session.
Provides API functions for retrieving metadata and data preview for DDIC objects 
(tables, structures) and CDS Views via data preview endpoint.
"""
from typing import Optional
from ..http_request import HttpRequestParameters, request
from .ddic_types import DDIC_OBJECT_TYPES


def get_ddic_metadata(
    http_request_parameters: HttpRequestParameters,
    object_name: str,
    object_type: DDIC_OBJECT_TYPES = "cds",
) -> str:
    """
    Fetch metadata for data preview-enabled objects (CDS Views and Transparent Tables).
    
    This endpoint is used by Eclipse ADT for data preview functionality. It returns
    metadata including column definitions, data types, key attributes, etc.
    
    **Important:** This endpoint ONLY works for objects that support data preview:
    - CDS Views (Core Data Services)
    - Transparent Tables (database tables)
    
    This does NOT work for:
    - DDIC Structures (no data preview)
    - Table Types (no data preview)
    - Data Elements (no data preview)
    - Domains (no data preview)
    - Database Views (use CDS or different endpoint)
    
    Args:
        http_request_parameters: HTTP request parameters from ADT client
        object_name: Name of the CDS view or transparent table
        object_type: "cds" for CDS Views or "ddic" for transparent tables
    
    Returns:
        Raw metadata XML response as string
    
    Raises:
        Exception: If metadata fetch fails or object doesn't support data preview
    
    Examples:
        >>> # Get CDS View metadata
        >>> metadata = get_ddic_metadata(http_params, "ZI_HEADCUST", "cds")
        >>> 
        >>> # Get transparent table metadata
        >>> metadata = get_ddic_metadata(http_params, "MARA", "ddic")
    """
    # All DDIC types use "ddic" endpoint, CDS uses "cds" endpoint
    preview_type = "cds" if object_type == "cds" else "ddic"
    
    # Build the data preview metadata URI
    # Pattern: /sap/bc/adt/datapreview/{preview_type}/{OBJECT_NAME}/metadata
    uri = f"/sap/bc/adt/datapreview/{preview_type}/{object_name}/metadata"
    
    # Make GET request with appropriate Accept header
    response = request(
        http_request_parameters=http_request_parameters,
        uri=uri,
        method="GET",
        body="",
        params={},
        content_type="application/vnd.sap.adt.datapreview.table.v1+xml",
    )

    if response.status_code == 200:
        return response.text
    else:
        # Simple label for error message
        label = "CDS View" if object_type == "cds" else "table"
        raise Exception(
            f"{response.status_code} - Failed to get {label} metadata for {object_name}.\n{response.text}"
        )


def preview_ddic_data(
    http_request_parameters: HttpRequestParameters,
    object_name: str,
    sql_query: str,
    row_number: int = 100,
) -> str:
    """
    Execute a SQL query and retrieve data preview for a DDIC object (table or CDS view).
    
    This endpoint is used by Eclipse ADT for data preview functionality. It executes
    a SQL query against the object and returns the result set with column metadata.
    
    **Important:** This endpoint works for objects that support data preview:
    - Database Tables (transparent tables)
    - CDS Views (Core Data Services)
    
    Args:
        http_request_parameters: HTTP request parameters from ADT client
        object_name: Name of the table or CDS view to query
        sql_query: SQL query to execute (SELECT statement)
        row_number: Maximum number of rows to return (default: 100)
    
    Returns:
        Raw data preview XML response as string containing:
        - Column metadata (names, types, descriptions, key attributes)
        - Data rows organized by column
        - Total row count and query execution time
    
    Raises:
        Exception: If data preview fails
    
    Examples:
        >>> # Preview table data
        >>> sql = "SELECT * FROM ZDT_SD_RULE"
        >>> data = preview_ddic_data(http_params, "ZDT_SD_RULE", sql, row_number=50)
        >>> 
        >>> # Preview with filter
        >>> sql = "SELECT MATNR, MAKTX FROM MARA WHERE MTART = 'ZMAT'"
        >>> data = preview_ddic_data(http_params, "MARA", sql, row_number=100)
    """
    
    # Build the data preview URI with query parameters
    # Pattern: /sap/bc/adt/datapreview/ddic?rowNumber={num}&ddicEntityName={name}
    uri = f"/sap/bc/adt/datapreview/ddic"
    
    params = {
        "rowNumber": str(row_number),
        "ddicEntityName": object_name,
    }
    
    # Make POST request with SQL query as body
    # Content-Type: text/plain
    # Accept: application/xml, application/vnd.sap.adt.datapreview.table.v1+xml
    response = request(
        http_request_parameters=http_request_parameters,
        uri=uri,
        method="POST",
        body=sql_query,
        params=params,
        content_type="text/plain",
        accept="application/xml, application/vnd.sap.adt.datapreview.table.v1+xml",
    )

    if response.status_code == 200:
        return response.text
    else:
        raise Exception(
            f"{response.status_code} - Failed to preview data for {object_name}.\n{response.text}"
        )
