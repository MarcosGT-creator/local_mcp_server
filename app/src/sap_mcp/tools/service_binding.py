"""
Service binding tools for SAP ADT.
Includes service binding creation and publishing.
"""

import logging
from typing import Literal
from pydantic import Field
from fastmcp.tools import tool as _tool
from typing import Callable, Any
tool: Callable[..., Any] = _tool  # type: ignore[assignment]

from ._helpers import get_adt_client_safe

logger = logging.getLogger(__name__)


@tool
def create_and_publish_service_binding(
    name: str = Field(
        ...,
        description="Name of the service binding (e.g., 'Z_MY_SERVICE_UI'). Must start with Z or Y.",
    ),
    description: str = Field(
        ...,
        description="Description of the service binding",
    ),
    service_definition: str = Field(
        ...,
        description="Name of the service definition to bind (e.g., 'Z_MY_SERVICE_DEF'). Must exist.",
    ),
    package: str = Field(
        "$TMP",
        description="Package name. Use '$TMP' for local objects or specify transport package.",
    ),
    binding_version: Literal["ODATA\\CV4", "ODATA\\CV2", "SQL", "INA"] = Field(
        "ODATA\\CV4",
        description="Type of service binding: ODATA\\CV4 (OData V4), ODATA\\CV2 (OData V2), SQL (SQL Service), INA (Analytics)",
    ),
    corr_nr: str = Field(
        "",
        description="Transport request number (required for custom packages like ZBRIM*, optional for $TMP). Leave empty for $TMP or if you want the system to prompt.",
    ),
) -> str:
    """
    Create and publish a complete SAP service binding in one operation.

    This tool orchestrates the full workflow:
    1. Creates the service binding
    2. Activates it
    3. Publishes it to make the OData endpoint available

    Perfect for quickly exposing CDS views or service definitions as OData services.

    **Prerequisites:**
    - Service definition must exist (create with create_object type SRVD/SRV first)
    - Must have developer access to the package

    **Workflow Steps:**
    1. **Create**: POST to /sap/bc/adt/businessservices/bindings with XML body
    2. **Activate**: Activate the service binding object
    3. **Publish**: POST to /sap/bc/adt/businessservices/odatav4/publishjobs

    **Use Cases:**
    - Create OData V4 UI service for Fiori apps
    - Expose analytics services
    - Create API endpoints for external integration

    **Examples:**
        >>> # Create and publish OData V4 service binding in $TMP
        >>> create_and_publish_service_binding(
        ...     name="Z_CUSTOMER_UI",
        ...     description="Customer Management UI Service",
        ...     service_definition="Z_CUSTOMER_DEF",
        ...     package="$TMP",
        ...     binding_version="ODATA\\CV4"
        ... )

        >>> # Create OData V2 service in custom package with transport
        >>> create_and_publish_service_binding(
        ...     name="Z_SALES_API",
        ...     description="Sales Order API",
        ...     service_definition="Z_SALES_DEF",
        ...     package="ZBRIM_PKG",
        ...     binding_version="ODATA\\CV2",
        ...     corr_nr="D2AK123456"
        ... )

    **Returns:**
        Success message with service URLs or error details
    """
    adt_client = get_adt_client_safe()
    if isinstance(adt_client, str):
        return adt_client  # Error message

    try:
        # Step 1: Create Service Binding
        logger.info(
            "Step 1/3: Creating service binding",
            extra={"name": name, "package": package},
        )

        # Prepare corr_nr parameter
        transport_nr = corr_nr if corr_nr else None

        try:
            create_result = adt_client.create_service_binding(
                name=name,
                description=description,
                package=package,
                service_definition=service_definition,
                service_binding_version=binding_version,
                corr_nr=transport_nr,
            )
        except Exception as create_error:
            logger.error(
                "Failed to create service binding",
                extra={"name": name, "error": str(create_error)},
            )
            return f"Step 1 FAILED - Create service binding '{name}': {str(create_error)}"

        if not create_result or not isinstance(create_result, dict):
            return f"Step 1 FAILED - Create service binding '{name}' returned invalid result"

        logger.info(
            "Service binding created successfully",
            extra={"name": name, "result": create_result},
        )

        # The create_result is a dictionary with uri, etag, etc.
        object_uri = create_result.get(
            "uri", f"/sap/bc/adt/businessservices/bindings/{name.lower()}"
        )

        # Step 2: Activate Service Binding
        logger.info("Step 2/3: Activating service binding", extra={"name": name})

        try:
            activate_result = adt_client.activate(object_name=name, object_uri=object_uri)
        except Exception as activate_error:
            logger.error(
                "Failed to activate service binding",
                extra={"name": name, "error": str(activate_error)},
            )
            return f"Step 2 FAILED - Activate service binding '{name}': {str(activate_error)}"

        if not activate_result:
            return f"Step 2 FAILED - Activate service binding '{name}' returned False"

        logger.info("Service binding activated successfully", extra={"name": name})

        # Step 3: Publish Service Binding
        logger.info("Step 3/3: Publishing service binding", extra={"name": name})

        try:
            publish_result = adt_client.publish_service_binding(name)
        except Exception as publish_error:
            logger.error(
                "Failed to publish service binding",
                extra={"name": name, "error": str(publish_error)},
            )
            return f"Step 3 FAILED - Publish service binding '{name}': {str(publish_error)}"

        # Check publish result severity
        if not isinstance(publish_result, dict):
            return f"Step 3 FAILED - Publish service binding '{name}' returned invalid result"

        severity = publish_result.get("severity", "").upper()
        short_text = publish_result.get("short_text", "")
        long_text = publish_result.get("long_text", "")

        # Check for errors (severity: ERROR or FATAL)
        if severity in ["ERROR", "FATAL"]:
            logger.error(
                "Service binding publish failed",
                extra={
                    "name": name,
                    "severity": severity,
                    "short_text": short_text,
                    "long_text": long_text,
                },
            )
            return f"Step 3 FAILED - Publish service binding '{name}': {short_text}\n{long_text}"

        # Warnings are acceptable but should be logged
        if severity == "WARNING":
            logger.warning(
                "Service binding published with warnings",
                extra={
                    "name": name,
                    "short_text": short_text,
                    "long_text": long_text,
                },
            )

        logger.info(
            "Service binding published successfully",
            extra={"name": name, "result": publish_result},
        )

        # Generate service URLs
        base_url = adt_client.sap_host.rstrip("/")
        service_name_lower = name.lower()

        if "V4" in binding_version:
            service_url = (
                f"{base_url}/sap/opu/odata4/sap/{service_name_lower}/srvd_a2x/0001/"
            )
            metadata_url = f"{service_url}$metadata"
        elif "V2" in binding_version:
            service_url = f"{base_url}/sap/opu/odata/sap/{service_name_lower}/"
            metadata_url = f"{service_url}$metadata"
        else:
            service_url = (
                f"{base_url}/sap/bc/adt/businessservices/bindings/{service_name_lower}"
            )
            metadata_url = ""

        # Build success message
        result = f"✅ Service binding '{name}' created, activated, and published successfully!\n\n"
        
        # Add publish status details
        result += f"Status: {severity}\n"
        if short_text:
            result += f"Message: {short_text}\n"
        
        # Add warning details if present
        if severity == "WARNING" and long_text:
            result += f"\n⚠️ Warning Details:\n{long_text}\n"
        
        # Add service URLs
        if "V4" in binding_version or "V2" in binding_version:
            result += f"\n📍 Service URL: {service_url}\n"
            if metadata_url:
                result += f"📍 Metadata URL: {metadata_url}\n"

        return result

    except Exception as e:
        error_msg = str(e)
        logger.error(
            "Unexpected error in service binding workflow",
            extra={
                "name": name,
                "service_definition": service_definition,
                "error_type": type(e).__name__,
                "error": error_msg,
            },
        )
        return f"UNEXPECTED ERROR - Service binding workflow: {error_msg}"


@tool
def get_service_binding_types() -> str:
    """
    Get available service binding types from the SAP system.

    This tool retrieves all available service binding types that can be used
    when creating or publishing service bindings.

    **Returns:**
        JSON string with list of available binding types, each containing:
        - name: Binding type name
        - description: Description of the binding type
        - data: Technical binding type identifier

    **Example:**
        >>> # Get all available binding types
        >>> types = get_service_binding_types()
        >>> # Use the information to choose correct type for create_and_publish_service_binding
    """
    import json
    
    adt_client = get_adt_client_safe()
    if isinstance(adt_client, str):
        return adt_client  # Error message

    try:
        binding_types = adt_client.get_binding_types()
        return json.dumps(binding_types, indent=2)
    except Exception as e:
        logger.error(
            "Error getting service binding types",
            extra={"error_type": type(e).__name__, "error_message": str(e)},
        )
        return f"Failed to get service binding types: {str(e)}"
