"""
Service Binding Operations for SAP ADT API

Service Bindings (SRVB/SVB) are special objects that expose service definitions
as consumable services (OData V2, OData V4, SQL, INA).

Operations:
- create_service_binding: Create a new service binding
- publish_service_binding: Publish service binding to make it accessible
- unpublish_service_binding: Unpublish/deactivate service binding
"""

import xml.etree.ElementTree as ET
from typing import Literal, TypedDict, Dict
from ..http_request import HttpRequestParameters, request


ServiceBindingVersion = Literal["ODATA\\CV4", "ODATA\\CV2", "SQL", "INA"]


class ServiceBindingPublishStatus(TypedDict):
    severity: str  # "OK", "ERROR", "WARNING"
    short_text: str
    long_text: str


# Constants for service binding configuration
BINDING_VERSION_MAPPING: Dict[str, Dict[str, str]] = {
    "ODATA\\CV4": {"type": "ODATA", "version": "V4", "category": "1"},
    "ODATA\\CV2": {"type": "ODATA", "version": "V2", "category": "1"},
    "SQL": {"type": "SQL", "version": "", "category": "1"},
    "INA": {"type": "INA", "version": "", "category": "1"},
}

PUBLISH_ENDPOINTS: Dict[str, str] = {
    "odatav4": "/sap/bc/adt/businessservices/odatav4/publishjobs",
    "odatav2": "/sap/bc/adt/businessservices/odatav2/publishjobs",
    "sql": "/sap/bc/adt/businessservices/sql/publishjobs",
    "ina": "/sap/bc/adt/businessservices/ina/publishjobs",
}

UNPUBLISH_ENDPOINTS: Dict[str, str] = {
    "odatav4": "/sap/bc/adt/businessservices/odatav4/unpublishjobs",
    "odatav2": "/sap/bc/adt/businessservices/odatav2/unpublishjobs",
    "sql": "/sap/bc/adt/businessservices/sql/unpublishjobs",
    "ina": "/sap/bc/adt/businessservices/ina/unpublishjobs",
}


def _parse_status_response(response_text: str) -> ServiceBindingPublishStatus:
    """
    Parse SAP status message XML response.
    
    Args:
        response_text: XML response text
        
    Returns:
        ServiceBindingPublishStatus with severity, short_text, long_text
    """
    try:
        root = ET.fromstring(response_text)
        
        severity = ""
        short_text = ""
        long_text = ""
        
        for elem in root.iter():
            if elem.tag.endswith("SEVERITY"):
                severity = elem.text or ""
            elif elem.tag.endswith("SHORT_TEXT"):
                short_text = elem.text or ""
            elif elem.tag.endswith("LONG_TEXT"):
                long_text = elem.text or ""
        
        return {
            "severity": severity,
            "short_text": short_text,
            "long_text": long_text,
        }
    except Exception:
        # If parsing fails, return a generic success status
        return {
            "severity": "OK",
            "short_text": "Operation completed",
            "long_text": response_text,
        }


def _build_service_binding_xml(
    name: str,
    package: str,
    description: str,
    service_definition: str,
    binding_attrs: Dict[str, str],
    username: str,
) -> str:
    """
    Build XML body for service binding creation.
    
    Args:
        name: Service binding name
        package: Package name
        description: Service binding description
        service_definition: Service definition name
        binding_attrs: Binding attributes (type, version, category)
        username: Responsible user
        
    Returns:
        XML string for service binding creation
    """
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<srvb:serviceBinding xmlns:adtcore="http://www.sap.com/adt/core" xmlns:srvb="http://www.sap.com/adt/ddic/ServiceBindings" adtcore:description="{description}" adtcore:language="EN" adtcore:name="{name}" adtcore:type="SRVB/SVB" adtcore:masterLanguage="EN" adtcore:masterSystem="D2A" adtcore:responsible="{username}">
  <adtcore:packageRef adtcore:name="{package}"/>
  <srvb:services srvb:name="{service_definition}">
    <srvb:content srvb:version="0001">
      <srvb:serviceDefinition adtcore:name="{service_definition}"/>
    </srvb:content>
  </srvb:services>
  <srvb:binding srvb:category="{binding_attrs['category']}" srvb:type="{binding_attrs['type']}" srvb:version="{binding_attrs['version']}">
    <srvb:implementation adtcore:name=""/>
  </srvb:binding>
</srvb:serviceBinding>"""


def create_service_binding(
    http_request_parameters: HttpRequestParameters,
    name: str,
    package: str,
    description: str,
    service_definition: str,
    username: str,
    service_binding_version: ServiceBindingVersion = "ODATA\\CV4",
    corr_nr: str | None = None,
) -> dict:
    """
    Create a new Service Binding.
    
    Service Bindings expose Service Definitions as consumable services.
    
    Args:
        http_request_parameters: HTTP request parameters
        name: Service binding name (e.g., "Z_MY_SERVICE_BIND")
        package: Package name (e.g., "$TMP" or "ZPACKAGE")
        description: Description of the service binding
        service_definition: Name of the service definition to bind (must exist)
        username: SAP username for responsible field
        service_binding_version: Binding type/version
            - "ODATA\\CV4": OData V4 (modern RAP)
            - "ODATA\\CV2": OData V2 (legacy Gateway)
            - "SQL": SQL Service
            - "INA": InA Service (Analytics)
        corr_nr: Transport request number (required for custom packages, optional for $TMP)
    
    Returns:
        Dictionary with uri, etag, and other metadata from response
        
    Raises:
        Exception if creation fails
        
    Example:
        >>> # Create in $TMP (no transport needed)
        >>> result = create_service_binding(
        ...     http_params,
        ...     name="Z_CUSTOMER_API",
        ...     package="$TMP",
        ...     description="Customer API Service Binding",
        ...     service_definition="Z_CUSTOMER_DEF",
        ...     username="MYUSER",
        ...     service_binding_version="ODATA\\CV4"
        ... )
        >>> 
        >>> # Create in custom package (transport required)
        >>> result = create_service_binding(
        ...     http_params,
        ...     name="Z_CUSTOMER_API",
        ...     package="ZBRIM_PKG",
        ...     description="Customer API Service Binding",
        ...     service_definition="Z_CUSTOMER_DEF",
        ...     username="MYUSER",
        ...     service_binding_version="ODATA\\CV4",
        ...     corr_nr="D2AK123456"
        ... )
        >>> print(result["uri"])  # /sap/bc/adt/businessservices/bindings/z_customer_api
    """
    # Get binding attributes from mapping
    binding_attrs = BINDING_VERSION_MAPPING.get(
        service_binding_version,
        BINDING_VERSION_MAPPING["ODATA\\CV4"]  # Default to V4
    )
    
    # Build XML body for service binding creation
    body = _build_service_binding_xml(
        name=name,
        package=package,
        description=description,
        service_definition=service_definition,
        binding_attrs=binding_attrs,
        username=username,
    )
    
    # Build params - add transport if provided
    params = {}
    if corr_nr:
        params["corrNr"] = corr_nr
    
    # Create the service binding
    response = request(
        http_request_parameters=http_request_parameters,
        uri="/sap/bc/adt/businessservices/bindings",
        method="POST",
        body=body,
        params=params,
        content_type="application/vnd.sap.adt.businessservices.servicebinding.v2+xml",
        accept="application/vnd.sap.adt.businessservices.servicebinding.v1+xml, application/vnd.sap.adt.businessservices.servicebinding.v2+xml",
    )
    
    if 200 <= response.status_code <= 300:
        # Extract URI from Location header
        uri = response.headers.get("Location", "")
        etag = response.headers.get("ETag", "")
        
        return {
            "uri": uri,
            "etag": etag,
            "status_code": response.status_code,
            "response_body": response.text,
        }
    else:
        raise Exception(
            f"{response.status_code} - Failed to create service binding {name}\n{response.text}"
        )


def publish_service_binding(
    http_request_parameters: HttpRequestParameters,
    name: str,
    binding_type: Literal["odatav4", "odatav2", "sql", "ina"] = "odatav4",
) -> ServiceBindingPublishStatus:
    """
    Publish a Service Binding to make it accessible.
    
    Publishing activates the service binding and makes it available for consumption.
    For OData services, this creates the service endpoint.
    
    Args:
        http_request_parameters: HTTP request parameters
        name: Service binding name
        binding_type: Type of binding to publish
            - "odatav4": OData V4 service
            - "odatav2": OData V2 service
            - "sql": SQL service
            - "ina": InA service
    
    Returns:
        ServiceBindingPublishStatus with severity, short_text, long_text
        
    Raises:
        Exception if publish fails
        
    Example:
        >>> status = publish_service_binding(
        ...     http_params,
        ...     name="Z_CUSTOMER_API",
        ...     binding_type="odatav4"
        ... )
        >>> print(status["short_text"])  # "Z_CUSTOMER_API published locally"
    """
    # Build XML body
    body = f"""<?xml version="1.0" encoding="UTF-8"?>
        <adtcore:objectReferences xmlns:adtcore="http://www.sap.com/adt/core">
            <adtcore:objectReference adtcore:type="SCGR" adtcore:name="{name}"/>
        </adtcore:objectReferences>"""
    
    # Get endpoint from mapping
    endpoint = PUBLISH_ENDPOINTS.get(binding_type)
    if not endpoint:
        raise ValueError(f"Unknown binding type: {binding_type}. Valid types: {list(PUBLISH_ENDPOINTS.keys())}")
    
    response = request(
        http_request_parameters=http_request_parameters,
        uri=endpoint,
        method="POST",
        body=body,
        params={},
        content_type="application/xml",
        accept="application/xml, application/vnd.sap.as+xml;charset=UTF-8;dataname=com.sap.adt.StatusMessage",
    )
    
    if 200 <= response.status_code <= 300:
        return _parse_status_response(response.text)
    else:
        raise Exception(
            f"{response.status_code} - Failed to publish service binding {name}\n{response.text}"
        )


def unpublish_service_binding(
    http_request_parameters: HttpRequestParameters,
    name: str,
    binding_type: Literal["odatav4", "odatav2", "sql", "ina"] = "odatav4",
) -> ServiceBindingPublishStatus:
    """
    Unpublish a Service Binding to deactivate it.
    
    Unpublishing removes the service endpoint and makes it unavailable for consumption.
    
    Args:
        http_request_parameters: HTTP request parameters
        name: Service binding name
        binding_type: Type of binding to unpublish
            - "odatav4": OData V4 service
            - "odatav2": OData V2 service
            - "sql": SQL service
            - "ina": InA service
    
    Returns:
        ServiceBindingPublishStatus with severity, short_text, long_text
        
    Raises:
        Exception if unpublish fails
        
    Example:
        >>> status = unpublish_service_binding(
        ...     http_params,
        ...     name="Z_CUSTOMER_API",
        ...     binding_type="odatav4"
        ... )
        >>> print(status["short_text"])  # "Z_CUSTOMER_API unpublished locally"
    """
    # Build XML body
    body = f"""<?xml version="1.0" encoding="UTF-8"?>
<adtcore:objectReferences xmlns:adtcore="http://www.sap.com/adt/core">
    <adtcore:objectReference adtcore:type="SCGR" adtcore:name="{name}"/>
</adtcore:objectReferences>"""
    
    # Get endpoint from mapping
    endpoint = UNPUBLISH_ENDPOINTS.get(binding_type)
    if not endpoint:
        raise ValueError(f"Unknown binding type: {binding_type}. Valid types: {list(UNPUBLISH_ENDPOINTS.keys())}")
    
    response = request(
        http_request_parameters=http_request_parameters,
        uri=endpoint,
        method="POST",
        body=body,
        params={},
        content_type="application/xml",
        accept="application/xml, application/vnd.sap.as+xml;charset=UTF-8;dataname=com.sap.adt.StatusMessage",
    )
    
    if 200 <= response.status_code <= 300:
        return _parse_status_response(response.text)
    else:
        raise Exception(
            f"{response.status_code} - Failed to unpublish service binding {name}\n{response.text}"
        )


def get_binding_types(
    http_request_parameters: HttpRequestParameters,
) -> list:
    """
    Get available service binding types from the SAP system.
    
    Returns list of available binding types like:
    - INA
    - ODATA V2 (UI)
    - ODATA V2 (Web API)  
    - ODATA V4 (UI)
    - ODATA V4 (Web API)
    - SQL
    
    Returns:
        List of dictionaries with name, description, data keys
        
    Example:
        >>> types = get_binding_types(http_params)
        >>> for t in types:
        ...     print(f"{t['name']}: {t['data']}")
    """
    response = request(
        http_request_parameters=http_request_parameters,
        uri="/sap/bc/adt/businessservices/bindings/bindingtypes",
        method="GET",
        body="",
        params={},
        accept="application/xml, application/vnd.sap.adt.nameditems.v1+xml",
    )
    
    if response.status_code == 200:
        try:
            root = ET.fromstring(response.text)
            
            binding_types = []
            for item in root.findall(".//{http://www.sap.com/adt/nameditem}namedItem"):
                name_elem = item.find("{http://www.sap.com/adt/nameditem}name")
                desc_elem = item.find("{http://www.sap.com/adt/nameditem}description")
                data_elem = item.find("{http://www.sap.com/adt/nameditem}data")
                
                binding_types.append({
                    "name": name_elem.text if name_elem is not None else "",
                    "description": desc_elem.text if desc_elem is not None else "",
                    "data": data_elem.text if data_elem is not None else "",
                })
            
            return binding_types
        except Exception as e:
            raise Exception(f"Failed to parse binding types: {e}\n{response.text}")
    else:
        raise Exception(
            f"{response.status_code} - Failed to get binding types\n{response.text}"
        )
