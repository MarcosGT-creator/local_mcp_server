"""
oData API operations using ADT client session and credentials.
Uses sap-odata-python library for OData V2/V4 calls.
"""
from typing import Optional, Literal, Dict, Any
from sap_odata import ODataClient
from ..http_request import HttpRequestParameters
from ...utils.logger import logger


def _create_odata_client(http_request_parameters: HttpRequestParameters) -> ODataClient:
    """
    Create ODataClient using existing ADT session.
    
    Args:
        http_request_parameters: HTTP request parameters from ADT client
    
    Returns:
        Configured ODataClient instance with injected session
    """
    client = ODataClient(
        host=http_request_parameters["host"],
        client=http_request_parameters["client"],
        verify_ssl=True,
        timeout=120,
    )
    # Inject the existing authenticated ADT session
    client.session = http_request_parameters["session"]
    client.sap_mode = True
    return client


def get_odata_metadata(
    http_request_parameters: HttpRequestParameters,
    service_name: str,
    service_namespace: Optional[str] = None,
    odata_version: Literal["v2", "v4"] = "v4"
) -> str:
    """
    Fetch raw metadata XML from an oData service (V2 or V4).
    
    Args:
        http_request_parameters: HTTP request parameters from ADT client
        service_name: oData service name
        service_namespace: Service namespace (optional for v2, required for v4)
        odata_version: oData version ("v2" or "v4")
    
    Returns:
        Raw metadata XML as string
    
    Raises:
        Exception: If metadata fetch fails
    """
    logger.info(
        f"Fetching oData {odata_version} metadata",
        extra_fields={
            "service_name": service_name,
            "service_namespace": service_namespace
        }
    )
    
    try:
        client = _create_odata_client(http_request_parameters)
        
        xml = client.metadata(
            service=service_name,
            version=odata_version,
            namespace=service_namespace or ""
        )
        
        logger.info(
            "Metadata retrieved successfully",
            extra_fields={
                "service_name": service_name,
                "xml_length": len(xml)
            }
        )
        
        if xml.strip() == "":
            return "Failed to fetch metadata. Try connecting to test client 120 or 300."
        
        return xml
        
    except Exception as e:
        error_msg = f"Failed to fetch metadata: {str(e)}"
        logger.error(error_msg)
        raise Exception(error_msg)


def call_odata_service(
    http_request_parameters: HttpRequestParameters,
    http_method: str,
    service_name: str,
    entity_name: str,
    service_namespace: Optional[str] = None,
    odata_version: Literal["v2", "v4"] = "v4",
    query_parameters: Optional[Dict[str, Any]] = None,
    request_body: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Call an oData service with any HTTP method.
    
    Args:
        http_request_parameters: HTTP request parameters from ADT client
        http_method: HTTP method (GET, POST, PUT, PATCH, DELETE)
        service_name: oData service name
        entity_name: Entity name or path
        service_namespace: Service namespace (optional for v2, required for v4)
        odata_version: oData version ("v2" or "v4")
        query_parameters: Query parameters dict
        request_body: Request body for POST/PUT/PATCH operations
    
    Returns:
        Dictionary containing API response data
    
    Raises:
        Exception: If API call fails
    """
    logger.info(
        f"Calling oData {odata_version} service",
        extra_fields={
            "method": http_method,
            "service_name": service_name,
            "entity_name": entity_name,
            "params": query_parameters
        }
    )
    
    try:
        client = _create_odata_client(http_request_parameters)
        method = http_method.upper()
        namespace = service_namespace or ""
        params = query_parameters or {}
        
        # Call appropriate method based on HTTP method
        if method == "GET":
            result = client.get(
                service=service_name,
                entity=entity_name,
                version=odata_version,
                namespace=namespace,
                **params
            )
        elif method == "POST":
            result = client.post(
                service=service_name,
                entity=entity_name,
                data=request_body or {},
                version=odata_version,
                namespace=namespace
            )
        elif method == "PATCH":
            result = client.patch(
                service=service_name,
                entity=entity_name,
                data=request_body or {},
                version=odata_version,
                namespace=namespace
            )
        elif method == "PUT":
            result = client.put(
                service=service_name,
                entity=entity_name,
                data=request_body or {},
                version=odata_version,
                namespace=namespace
            )
        elif method == "DELETE":
            result = client.delete(
                service=service_name,
                entity=entity_name,
                version=odata_version,
                namespace=namespace
            )
        else:
            raise Exception(f"Unsupported HTTP method: {method}")
        
        return {
            "status_code": 200,
            "data": result,
        }
        
    except Exception as e:
        error_msg = f"Failed to call oData service: {str(e)}"
        logger.error(error_msg)
        raise Exception(error_msg)
