"""
OData service tools for SAP ADT.
Includes metadata retrieval and generic API calls.
"""

import logging
from typing import Optional, Dict, Any, Literal
from pydantic import Field
from fastmcp.tools import tool as _tool
from typing import Callable, Any
tool: Callable[..., Any] = _tool  # type: ignore[assignment]

from ._helpers import get_adt_client_safe

logger = logging.getLogger(__name__)


@tool
def get_metadata(
    service_name: str = Field(
        ...,
        description="SAP OData service name (e.g., 'ZSD_ITEMS_LLM', 'SALESORDER_SRV', 'ZMY_CUSTOMER_API'). Use search_object() to find exact service names.",
    ),
    service_namespace: Optional[str] = Field(
        None,
        description="Service namespace (defaults to service_name if not provided). Example: 'ZSB_ITEMS_LLM'. Required for OData v4 services, optional for v2.",
    ),
    odata_version: Literal["v2", "v4"] = Field(
        "v4",
        description="OData version: 'v2' for legacy Gateway services or 'v4' for modern RAP services. Most new services use v4.",
    ),
) -> str:
    """
    Get oData service metadata from SAP system.

    This tool retrieves the metadata XML for an oData service, which describes the service structure,
    entity types, properties, associations, and operations available in the service.

    Uses the existing ADT client session and credentials for consistent authentication
    and session management across all SAP operations.

    **Finding Service Details:**
    - Use `search_object()` to find the service name and determine if it's v2 or v4
    - oData v4 services typically have namespaces (e.g., ZMY_SERVICE with namespace ZMY_SERVICE_NS)
    - oData v2 services may not require a namespace
    - Search pattern: If user provides "ZMY_SERVICE", search for "Z*SERVICE*" to find exact name and namespace

    **Examples:**
        >>> # First search for the service
        >>> search_results = search_object("Z*CUSTOMER*", object_type="SRVD/SRV")
        >>> # Then get metadata for OData v4 service
        >>> metadata = get_metadata(
        ...     service_name="ZSD_CUSTOMER_API",
        ...     service_namespace="ZSB_CUSTOMER_API",
        ...     odata_version="v4"
        ... )

        >>> # Get metadata for OData v2 Gateway service
        >>> metadata = get_metadata(
        ...     service_name="ZMM_MATERIAL_SRV",
        ...     odata_version="v2"
        ... )

        >>> # Get metadata for OData v4 service (namespace defaults to service_name)
        >>> metadata = get_metadata(service_name="ZSALES_ORDER_API")

    **Returns:**
        String containing the metadata XML with entity definitions, properties, and associations

    **Common Use Cases:**
        - Understanding service structure before making API calls
        - Generating client code or documentation
        - Validating entity names and properties for call_sap_api_generic()
        - Troubleshooting service issues
    """
    adt_client = get_adt_client_safe()
    if isinstance(adt_client, str):
        return adt_client  # Error message

    if not service_name:
        return "Error: Service name is required"

    # Validate odata_version
    if odata_version not in ["v2", "v4"]:
        return "Error: oData version must be 'v2' or 'v4'"

    # Use service_name as namespace if not provided
    if not service_namespace:
        service_namespace = service_name

    try:
        # Use ADT client's oData metadata method (reuses session and credentials)
        metadata_xml = adt_client.get_odata_metadata(
            service_name=service_name,
            service_namespace=service_namespace,
            odata_version=odata_version,
        )

        logger.info(
            "Metadata retrieved successfully",
            extra={"service_name": service_name, "xml_length": len(metadata_xml) if metadata_xml else 0},
        )

        if len(metadata_xml) == 0:
            return "No data found. You may be connected to dev client (110/310). Use connect_to_sap to switch to test client (120/320) to access data."

        return metadata_xml

    except Exception as e:
        error_msg = str(e)
        logger.error(
            "Error retrieving metadata",
            extra={"error_type": type(e).__name__, "error": error_msg},
        )
        return f"Failed to retrieve metadata: {error_msg}"


@tool
def call_sap_api_generic(
    http_method: str = Field(
        ...,
        description="HTTP method to use: 'GET' (retrieve data), 'POST' (create), 'PUT' (full update), 'PATCH' (partial update), 'DELETE' (remove), 'HEAD', 'OPTIONS'",
    ),
    service_name: str = Field(
        ...,
        description="SAP OData service name (e.g., 'ZSD_CUSTOMER_API', 'SALESORDER_SRV'). Use search_object() and get_metadata() to find available services.",
    ),
    entity_name: str = Field(
        ...,
        description="Entity name or path. Examples: 'Customers', 'Products', 'Orders('12345')', 'Customers('CUST001')/Orders', 'Products('MAT123')/Details'",
    ),
    service_namespace: Optional[str] = Field(
        None,
        description="Service namespace only. Required for OData v4 services. Usually starts with 'ZSB*'. Use 'search_object()' to find exact namespace with object type 'SRVB/SVB'.",
    ),
    odata_version: Literal["v2", "v4"] = Field(
        "v4",
        description="OData version: 'v2' for Gateway services, 'v4' for RAP services. Check service type with search_object().",
    ),
    query_parameters: Optional[dict] = Field(
        None,
        description="Query parameters dict. Examples: {'$filter': 'Price gt 100', '$select': 'Name,Price', '$top': 10, '$skip': 20, '$orderby': 'Name desc'}",
    ),
    request_body: Optional[dict] = Field(
        None,
        description="Request body for POST/PUT/PATCH operations. Example: {'CustomerName': 'ACME Corp', 'Country': 'US', 'Active': true}",
    ),
) -> Dict[str, Any] | str:
    """
    To call any SAP oData service generically using specified HTTP method.

    **Prerequisites:**
    - Use `search_object()` to find the service and determine v2/v4
    - Use `get_metadata()` to understand available entities and properties
    - If not able to find service_namespace for v4, use `search_object()` with object type 'SRVB/SVB' to get exact namespace

    This tool provides a unified interface to interact with SAP oData services using any HTTP method.
    It automatically handles CSRF tokens for state-changing operations and supports both v2 and v4 oData.

    Uses the existing ADT client session and credentials for consistent authentication
    and session management across all SAP operations.

    **Common HTTP Methods:**
    - **GET**: Retrieve data (read operations)
    - **POST**: Create new records
    - **PATCH**: Update specific fields (recommended for updates)
    - **PUT**: Replace entire record (full update)
    - **DELETE**: Remove records

    **Query Parameters Examples:**
    - `{"$filter": "Price gt 100"}` - Filter records
    - `{"$select": "Name,Price,Category"}` - Select specific fields
    - `{"$top": 10}` - Limit number of records
    - `{"$skip": 20}` - Skip records (pagination)
    - `{"$orderby": "Name desc"}` - Sort results
    - `{"$expand": "Orders"}` - Include related data

    **Examples:**
        >>> # GET: Retrieve all customers
        >>> response = call_sap_api_generic(
        ...     http_method="GET",
        ...     service_name="ZSD_CUSTOMER_API",
        ...     service_namespace="ZSB_CUSTOMER_API",
        ...     odata_version="v4",
        ...     entity_name="Customers",
        ...     query_parameters={"$top": 10, "$select": "CustomerID,Name,Country"}
        ... )

        >>> # GET: Retrieve specific customer with filter
        >>> response = call_sap_api_generic(
        ...     http_method="GET",
        ...     service_name="ZSD_CUSTOMER_API",
        ...     odata_version="v2",
        ...     entity_name="Customers",
        ...     query_parameters={"$filter": "Country eq 'US' and Active eq true"}
        ... )

        >>> # POST: Create new customer
        >>> response = call_sap_api_generic(
        ...     http_method="POST",
        ...     service_name="ZSD_CUSTOMER_API",
        ...     entity_name="Customers",
        ...     odata_version="v2",
        ...     request_body={
        ...         "CustomerID": "CUST123",
        ...         "Name": "ACME Corporation",
        ...         "Country": "US",
        ...         "Active": True
        ...     }
        ... )
    """
    adt_client = get_adt_client_safe()
    if isinstance(adt_client, str):
        return adt_client  # Error message

    if not service_name:
        return "Error: Service name is required"

    if not entity_name:
        return "Error: Entity name is required"

    # Validate odata_version
    if odata_version not in ["v2", "v4"]:
        return "Error: oData version must be 'v2' or 'v4'"

    # Use service_name as namespace if not provided
    if not service_namespace:
        service_namespace = service_name

    try:
        # Use ADT client's oData service method (reuses session and credentials)
        response_data = adt_client.call_odata_service(
            http_method=http_method,
            service_name=service_name,
            entity_name=entity_name,
            service_namespace=service_namespace,
            odata_version=odata_version,
            query_parameters=query_parameters,
            request_body=request_body,
        )

        logger.info(
            "oData service call successful",
            extra={"service_name": service_name, "entity_name": entity_name},
        )

        # Extract data from the response (response now has status_code and data)
        # Library returns raw V2/V4 JSON:
        # - V4: {"value": [...], "@odata.count": n}
        # - V2: {"d": {"results": [...], "__count": "n"}} or {"d": [...]}
        data = response_data.get("data", {})

        # Check for empty data in both V4 and V2 formats
        is_empty = False
        if odata_version == "v4":
            is_empty = "value" in data and len(data.get("value", [])) == 0
        else:  # v2
            d = data.get("d", {})
            if isinstance(d, dict):
                is_empty = len(d.get("results", [])) == 0 and not any(k for k in d.keys() if not k.startswith("_"))
            elif isinstance(d, list):
                is_empty = len(d) == 0

        if is_empty:
            return "No data found. You may be connected to dev client (110/310). Use connect_to_sap to switch to test client (120/320) to access data."

        # Return response with status code and data
        return response_data

    except Exception as e:
        error_msg = str(e)
        logger.error(
            "Error calling oData service",
            extra={"error_type": type(e).__name__, "error": error_msg},
        )
        return f"Failed to call oData service: {error_msg}"
