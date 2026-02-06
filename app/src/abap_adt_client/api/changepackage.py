"""
Change Package Assignment for ABAP Objects

This module implements the refactoring API for moving objects between packages.
Used to move objects from $TMP to transportable packages with transport assignment.
"""

from typing import Dict, Any
from ..http_request import HttpRequestParameters, request
from src.utils.logger import logger


def change_package(
    http_request_parameters: HttpRequestParameters,
    object_uri: str,
    object_name: str,
    object_type: str,
    old_package: str,
    new_package: str,
    transport_number: str
) -> Dict[str, Any]:
    """
    Change the package assignment of an SAP object.
    
    This uses the ADT refactoring API to move objects between packages,
    typically from $TMP to transportable packages with transport assignment.
    
    Args:
        http_request_parameters: HTTP request parameters
        object_uri: URI of the object (e.g., /sap/bc/adt/ddic/ddl/sources/zce_major_lines)
        object_name: Name of the object (e.g., ZCE_MAJOR_LINES)
        object_type: Type of object (e.g., DDLS/DF)
        old_package: Current package (e.g., $TMP)
        new_package: Target package (e.g., ZGET_SUBS_API_V2)
        transport_number: Transport request number (e.g., DHAK905086)
    
    Returns:
        Dict with success status and details
        
    Raises:
        Exception: If package change fails
    
    Note:
        The refactoring flow is:
        1. Evaluate - Check if change is possible
        2. Preview - Preview the changes
        3. Execute - Perform the package change
    """
    logger.info(f"Changing package for {object_name} from {old_package} to {new_package}")
    
    # Step 1: Evaluate if package change is possible
    logger.info(f"Step 1/3: Evaluating package change for {object_name}")
    
    evaluate_response = request(
        http_request_parameters,
        uri="/sap/bc/adt/refactorings",
        params={
            "step": "evaluate",
            "rel": "http://www.sap.com/adt/relations/refactoring/changepackage",
            "uri": object_uri
        },
        method="POST",
        body="",
        content_type="application/xml",
        accept="application/xml"
    )
    
    logger.info(f"Evaluate step completed for {object_name}")
    
    # Step 2: Preview the changes with new package and transport
    logger.info(f"Step 2/3: Previewing package change for {object_name}")
    
    preview_body = f"""<?xml version="1.0" encoding="UTF-8"?>
<changepackage:changePackageRefactoring xmlns:adtcore="http://www.sap.com/adt/core" 
                                        xmlns:changepackage="http://www.sap.com/adt/refactoring/changepackagerefactoring" 
                                        xmlns:generic="http://www.sap.com/adt/refactoring/genericrefactoring">
  <changepackage:oldPackage>{old_package}</changepackage:oldPackage>
  <changepackage:newPackage>{new_package}</changepackage:newPackage>
  <generic:genericRefactoring>
    <generic:title>Change Package Assignment of {object_name}</generic:title>
    <generic:adtObjectUri>{object_uri}</generic:adtObjectUri>
    <generic:affectedObjects>
      <generic:affectedObject adtcore:uri="{object_uri}" 
                              adtcore:type="{object_type}" 
                              adtcore:name="{object_name}" 
                              adtcore:packageName="{old_package}">
        <generic:userContent></generic:userContent>
        <generic:changePackageDelta>
          <generic:newPackage>{old_package}</generic:newPackage>
        </generic:changePackageDelta>
      </generic:affectedObject>
    </generic:affectedObjects>
    <generic:transport>{transport_number}</generic:transport>
    <generic:ignoreSyntaxErrorsAllowed>false</generic:ignoreSyntaxErrorsAllowed>
    <generic:ignoreSyntaxErrors>false</generic:ignoreSyntaxErrors>
    <generic:userContent></generic:userContent>
  </generic:genericRefactoring>
  <changepackage:userContent></changepackage:userContent>
</changepackage:changePackageRefactoring>"""
    
    preview_response = request(
        http_request_parameters,
        uri="/sap/bc/adt/refactorings",
        params={
            "step": "preview",
            "rel": "http://www.sap.com/adt/relations/refactoring/changepackage"
        },
        method="POST",
        body=preview_body,
        content_type="text/plain",
        accept="application/xml"
    )
    
    logger.info(f"Preview step completed for {object_name}")
    
    # Step 3: Execute the package change
    logger.info(f"Step 3/3: Executing package change for {object_name}")
    
    execute_body = f"""<?xml version="1.0" encoding="UTF-8"?>
<generic:genericRefactoring xmlns:adtcore="http://www.sap.com/adt/core" 
                            xmlns:generic="http://www.sap.com/adt/refactoring/genericrefactoring">
  <generic:title>Change Package Assignment of {object_name}</generic:title>
  <generic:adtObjectUri>{object_uri}</generic:adtObjectUri>
  <generic:affectedObjects>
    <generic:affectedObject adtcore:uri="{object_uri}" 
                            adtcore:type="{object_type}" 
                            adtcore:name="{object_name}" 
                            adtcore:packageName="{old_package}">
      <generic:userContent></generic:userContent>
      <generic:changePackageDelta>
        <generic:newPackage>{new_package}</generic:newPackage>
      </generic:changePackageDelta>
    </generic:affectedObject>
  </generic:affectedObjects>
  <generic:transport>{transport_number}</generic:transport>
  <generic:ignoreSyntaxErrorsAllowed>false</generic:ignoreSyntaxErrorsAllowed>
  <generic:ignoreSyntaxErrors>false</generic:ignoreSyntaxErrors>
  <generic:userContent></generic:userContent>
</generic:genericRefactoring>"""
    
    execute_response = request(
        http_request_parameters,
        uri="/sap/bc/adt/refactorings",
        params={"step": "execute"},
        method="POST",
        body=execute_body,
        content_type="text/plain",
        accept="application/xml"
    )
    
    if execute_response.status_code == 200:
        logger.info(f"Successfully changed package for {object_name} from {old_package} to {new_package}")
        return {
            "success": True,
            "object_name": object_name,
            "old_package": old_package,
            "new_package": new_package,
            "transport": transport_number,
            "message": f"Package changed successfully from {old_package} to {new_package}"
        }
    else:
        error_msg = f"Failed to change package for {object_name}: {execute_response.text}"
        logger.error(error_msg)
        raise Exception(error_msg)
