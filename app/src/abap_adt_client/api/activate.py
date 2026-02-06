import time
import re
from typing import List, Dict, Any, Union
from ..http_request import HttpRequestParameters, request
from ..response_parsing import find_xml_element_attributes, find_xml_elements_attributes
from src.utils.logger import logger
from .lock import check_objects_lockable


def activate(
    http_request_parameters: HttpRequestParameters, object_name: str, object_uri: str
) -> bool:

    body = f"""
    <?xml version="1.0" encoding="UTF-8"?>
    <adtcore:objectReferences xmlns:adtcore="http://www.sap.com/adt/core">
        <adtcore:objectReference adtcore:uri="{object_uri}" adtcore:name="{object_name}"/>
    </adtcore:objectReferences>
    """

    response = request(
        http_request_parameters,
        uri="/sap/bc/adt/activation",
        params={"method": "activate", "preauditRequested": "true"},
        body=body,
        method="POST",
        content_type="application/xml",
    )
    
    # Parse the response XML to check for errors
    import xml.etree.ElementTree as ET
    root = ET.fromstring(response.text)
    
    # Define namespaces
    ns = {
        'chkl': 'http://www.sap.com/adt/checklist',
        'adtcore': 'http://www.sap.com/adt/core'
    }
    
    # Check properties
    properties = find_xml_element_attributes(response.text, "chkl:properties")
    activation_executed = properties.get("activationExecuted") == "true"
    generation_executed = properties.get("generationExecuted") == "true"
    
    if not (activation_executed or generation_executed):
        msg_elements = find_xml_elements_attributes(response.text, "msg")
        raise Exception(f"{response.status_code} - Activation was not executed.\n{msg_elements}")
    
    # Check for errors in messages - this is the critical fix!
    messages = root.findall('.//chkl:message', ns)
    errors = []
    warnings = []
    
    for msg in messages:
        msg_type = msg.get('type', '')
        msg_text = msg.text or ''
        short_text_elem = msg.find('.//chkl:shortText', ns)
        if short_text_elem is not None and short_text_elem.text:
            msg_text = short_text_elem.text
        
        if msg_type == 'E':  # Error
            errors.append(msg_text)
        elif msg_type == 'W':  # Warning
            warnings.append(msg_text)
    
    # If there are errors, activation failed even though it was executed
    if errors:
        error_msg = '\n'.join([f"  - {err}" for err in errors])
        logger.error(f"Activation of '{object_name}' failed with errors:\n{error_msg}")
        raise Exception(
            f"Activation failed for '{object_name}' - Syntax/semantic errors found:\n{error_msg}"
        )
    
    # Log warnings but still return success
    if warnings:
        warning_msg = '\n'.join([f"  - {warn}" for warn in warnings])
        logger.warning(f"Activation of '{object_name}' completed with warnings:\n{warning_msg}")
    
    return True


def get_inactive_objects(http_request_parameters: HttpRequestParameters) -> List[Dict[str, Any]]:
    """
    Get list of inactive objects for the current user.
    
    Returns:
        List of inactive objects with their URIs, names, types, and transport info
    """
    response = request(
        http_request_parameters,
        uri="/sap/bc/adt/activation/inactiveobjects",
        method="GET",
        body="",
        params={},
        accept="application/vnd.sap.adt.inactivectsobjects.v1+xml, application/xml;q=0.8",
    )
    
    # Parse the XML response
    import xml.etree.ElementTree as ET
    
    root = ET.fromstring(response.text)
    
    # Define namespaces
    ns = {
        'ioc': 'http://www.sap.com/abapxml/inactiveCtsObjects',
        'adtcore': 'http://www.sap.com/adt/core'
    }
    
    inactive_objects = []
    
    # Parse each entry
    for entry in root.findall('.//ioc:entry', ns):
        obj_elem = entry.find('ioc:object', ns)
        transport_elem = entry.find('ioc:transport', ns)
        
        # Skip entries without object information
        if obj_elem is None:
            continue
            
        ref_elem = obj_elem.find('ioc:ref', ns)
        if ref_elem is None:
            continue
        
        # Extract object information
        obj_info: Dict[str, Any] = {
            'uri': ref_elem.get('{http://www.sap.com/adt/core}uri', ''),
            'type': ref_elem.get('{http://www.sap.com/adt/core}type', ''),
            'name': ref_elem.get('{http://www.sap.com/adt/core}name', ''),
            'user': obj_elem.get('{http://www.sap.com/abapxml/inactiveCtsObjects}user', ''),
            'deleted': obj_elem.get('{http://www.sap.com/abapxml/inactiveCtsObjects}deleted', 'false'),
        }
        
        # Extract transport information if available
        if transport_elem is not None:
            transport_ref = transport_elem.find('ioc:ref', ns)
            if transport_ref is not None:
                obj_info['transport'] = {
                    'uri': transport_ref.get('{http://www.sap.com/adt/core}uri', ''),
                    'type': transport_ref.get('{http://www.sap.com/adt/core}type', ''),
                    'name': transport_ref.get('{http://www.sap.com/adt/core}name', ''),
                    'description': transport_ref.get('{http://www.sap.com/adt/core}description', ''),
                    'user': transport_elem.get('{http://www.sap.com/abapxml/inactiveCtsObjects}user', ''),
                    'linked': transport_elem.get('{http://www.sap.com/abapxml/inactiveCtsObjects}linked', 'false'),
                }
        
        # Only add objects that have a name (skip empty entries)
        if obj_info['name']:
            inactive_objects.append(obj_info)
    
    return inactive_objects


def activate_multiple_objects(
    http_request_parameters: HttpRequestParameters,
    objects: List[Dict[str, str]],
    preaudit_requested: bool = False,
    max_poll_attempts: int = 60,
    poll_interval: int = 2
) -> Dict[str, Any]:
    """
    Activate multiple SAP objects in a single activation run.
    
    This uses the background activation job API which:
    1. Creates an activation run (returns run ID)
    2. Polls for completion status
    3. Returns the final result
    
    Args:
        http_request_parameters: HTTP request parameters
        objects: List of dicts with 'uri' and 'name' keys for each object
        preaudit_requested: Whether to request pre-activation audit (default: False)
        max_poll_attempts: Maximum number of polling attempts (default: 60)
        poll_interval: Seconds between poll attempts (default: 2)
    
    Returns:
        Dict with activation result including status and any messages
        
    Raises:
        Exception: If objects are locked or activation fails
    
    Note:
        Objects must NOT be locked before activation. If any object is locked by you or another user,
        unlock them first or the activation will fail.
    """
    logger.info(f"Preparing to activate {len(objects)} objects")
    
    # Validate objects list
    if not objects or len(objects) == 0:
        raise Exception("No objects provided for activation")
    
    # Step 0: Check if any objects are locked
    logger.info("Checking if objects are lockable...")
    lock_status = check_objects_lockable(http_request_parameters, objects)
    
    if lock_status['locked']:
        locked_names = ', '.join(lock_status['locked'])
        error_details = '\n'.join([
            f"  - {name}: {lock_status['errors'].get(name, 'Unknown error')}" 
            for name in lock_status['locked']
        ])
        logger.error(f"Cannot activate - objects are locked: {locked_names}")
        raise Exception(
            f"Cannot activate objects - the following objects are currently locked:\n"
            f"{error_details}\n\n"
            f"Please unlock these objects before attempting activation."
        )
    
    logger.info(f"All {len(lock_status['lockable'])} objects are lockable. Proceeding with activation.")
    
    # Step 1: Create activation run
    # Build XML body with multiple object references
    object_refs = []
    for obj in objects:
        uri = obj.get('uri', '')
        name = obj.get('name', '')
        if uri and name:
            object_refs.append(
                f'<adtcore:objectReference adtcore:uri="{uri}" adtcore:name="{name}"/>'
            )
    
    body = f"""<?xml version="1.0" encoding="UTF-8"?>
<adtcore:objectReferences xmlns:adtcore="http://www.sap.com/adt/core">
{"".join(object_refs)}
</adtcore:objectReferences>"""
    
    # Create the activation run
    try:
        response = request(
            http_request_parameters,
            uri="/sap/bc/adt/activation/runs",
            params={"method": "activate", "preauditRequested": str(preaudit_requested).lower()},
            body=body,
            method="POST",
            content_type="application/xml",
            accept="application/xml",
        )
    except Exception as e:
        error_msg = str(e)
        # Check for common lock-related errors
        if "locked" in error_msg.lower() or "is being edited" in error_msg.lower():
            logger.error(f"Objects are locked: {error_msg}")
            raise Exception(
                f"Cannot activate objects - one or more objects are currently locked. "
                f"Please unlock all objects before activation. Error: {error_msg}"
            )
        # Re-raise other errors
        raise
    
    # Extract run ID from Location header
    location = response.headers.get('Location', '')
    if not location:
        raise Exception("Failed to create activation run: No Location header in response")
    
    # Extract run ID from location (e.g., /sap/bc/adt/activation/runs/01FBA9E9BAA21FE0AEBD1F70B7BC1E49)
    run_id_match = re.search(r'/activation/runs/([A-F0-9]+)$', location)
    if not run_id_match:
        raise Exception(f"Failed to extract run ID from location: {location}")
    
    run_id = run_id_match.group(1)
    
    logger.info(f"Activation run created with ID: {run_id}, activating {len(objects)} objects")
    
    # Step 2: Poll for completion
    run_uri = f"/sap/bc/adt/activation/runs/{run_id}"
    
    for attempt in range(max_poll_attempts):
        logger.debug(f"Polling activation run {run_id}, attempt {attempt + 1}/{max_poll_attempts}")
        
        # Poll WITHOUT long polling to avoid hanging
        # Use regular polling with shorter intervals instead
        poll_response = request(
            http_request_parameters,
            uri=run_uri,
            params={},  # Removed withLongPolling to prevent hanging
            method="GET",
            body="",
            accept="application/xml, application/vnd.sap.adt.backgroundrun.v1+xml",
        )
        
        # Parse the response
        import xml.etree.ElementTree as ET
        root = ET.fromstring(poll_response.text)
        
        # Define namespace
        ns = {'runs': 'http://www.sap.com/adt/backgroundruns'}
        
        # Get status and progress
        status = root.get('{http://www.sap.com/adt/backgroundruns}status', '')
        progress = root.get('{http://www.sap.com/adt/backgroundruns}progressPercentage', '0')
        
        logger.info(f"Activation run {run_id}: status={status}, progress={progress}%")
        
        if status == 'finished':
            # Get result kind if available
            result_elem = root.find('.//runs:result', ns)
            result_kind = ''
            if result_elem is not None:
                result_kind = result_elem.get('{http://www.sap.com/adt/backgroundruns}kind', '')
            
            # Always fetch the detailed result directly from /sap/bc/adt/activation/results/{run_id}
            # This is what Eclipse ADT does - it doesn't rely on the link in the response
            result_uri = f"/sap/bc/adt/activation/results/{run_id}"
            
            try:
                result_response = request(
                    http_request_parameters,
                    uri=result_uri,
                    method="GET",
                    body="",
                    params={},
                    accept="application/xml",
                )
                
                # CRITICAL FIX: Check for errors in the activation result
                result_root = ET.fromstring(result_response.text)
                
                # The response uses different namespaces:
                # - chkl:messages is the root from http://www.sap.com/abapxml/checklist
                # - msg elements are direct children (no namespace prefix in your example)
                chkl_ns = {'chkl': 'http://www.sap.com/abapxml/checklist'}
                
                # Log the full result XML for debugging
                logger.info(f"Activation result XML for run {run_id}:\n{result_response.text}")
                
                # Find all msg elements with type='E' (errors)
                # Note: msg elements don't have namespace prefix in the response
                error_messages = []
                error_details_full = []
                
                for msg in result_root.findall('.//msg[@type="E"]'):
                    obj_descr = msg.get('objDescr', '')
                    line_num = msg.get('line', '')
                    href = msg.get('href', '')
                    
                    # Get shortText element
                    short_text_elem = msg.find('shortText')
                    if short_text_elem is not None:
                        # Get all txt sub-elements and join them
                        txt_elements = short_text_elem.findall('txt')
                        if txt_elements:
                            error_texts = [txt.text for txt in txt_elements if txt.text]
                            error_text = ' | '.join(error_texts)
                        else:
                            error_text = short_text_elem.text or 'Unknown error'
                    else:
                        error_text = 'Unknown error'
                    
                    # Build detailed error message with line number and location
                    error_detail = {
                        'object': obj_descr,
                        'error': error_text,
                        'line': line_num,
                        'href': href
                    }
                    error_details_full.append(error_detail)
                    
                    # Format the error message for display
                    if obj_descr:
                        msg_parts = [f"{obj_descr}: {error_text}"]
                        if line_num and line_num != '0':
                            msg_parts.append(f"(line {line_num})")
                        if href and '#start=' in href:
                            # Extract line and column from href like: /sap/bc/adt/ddic/ddl/sources/zce_discount_attributes/source/main#start=41,6
                            location = href.split('#start=')[-1] if '#start=' in href else ''
                            if location:
                                msg_parts.append(f"at {location}")
                        error_messages.append(f"  - {' '.join(msg_parts)}")
                    else:
                        error_messages.append(f"  - {error_text}")
                
                # Also log warning messages for visibility
                warning_messages = []
                for msg in result_root.findall('.//msg[@type="W"]'):
                    obj_descr = msg.get('objDescr', '')
                    
                    short_text_elem = msg.find('shortText')
                    if short_text_elem is not None:
                        txt_elements = short_text_elem.findall('txt')
                        if txt_elements:
                            warning_texts = [txt.text for txt in txt_elements if txt.text]
                            warning_text = ' | '.join(warning_texts)
                        else:
                            warning_text = short_text_elem.text or 'Unknown warning'
                    else:
                        warning_text = 'Unknown warning'
                    
                    if obj_descr:
                        warning_messages.append(f"  - {obj_descr}: {warning_text}")
                    else:
                        warning_messages.append(f"  - {warning_text}")
                
                if warning_messages:
                    logger.warning(f"Activation completed with {len(warning_messages)} warning(s):\n" + '\n'.join(warning_messages))
                
                # If there are errors, raise exception with details
                if error_messages:
                    error_details = '\n'.join(error_messages)
                    logger.error(f"Activation run {run_id} completed with errors:\n{error_details}")
                    
                    # Analyze errors and provide helpful tips
                    troubleshooting_tips = []
                    
                    # Check for common error patterns
                    for detail in error_details_full:
                        error_lower = detail['error'].lower()
                        
                        # Syntax errors
                        if 'unexpected keyword' in error_lower:
                            keyword = detail['error'].split('"')
                            if len(keyword) >= 2:
                                kw = keyword[1]
                                troubleshooting_tips.append(
                                    f"💡 Reserved keyword '{kw}' detected: Escape it with quotes like \"{kw}\" or rename the field"
                                )
                        
                        # Missing/inactive dependencies
                        if 'does not exist' in error_lower or 'not active' in error_lower:
                            # Extract object name from error
                            if '"' in detail['error']:
                                dep_obj = detail['error'].split('"')[1]
                                troubleshooting_tips.append(
                                    f"💡 Dependency issue: Activate '{dep_obj}' first, or activate all objects together"
                                )
                        
                        # Syntax errors with line numbers
                        if detail['line'] and detail['line'] != '0':
                            troubleshooting_tips.append(
                                f"💡 Check line {detail['line']} in {detail['object'] or 'the object'}"
                            )
                    
                    # Remove duplicates
                    troubleshooting_tips = list(dict.fromkeys(troubleshooting_tips))
                    
                    # Build final error message
                    error_msg = f"Activation run completed but {len(error_messages)} error(s) found:\n\n{error_details}"
                    
                    if troubleshooting_tips:
                        error_msg += f"\n\n🔧 Troubleshooting Tips:\n" + '\n'.join(troubleshooting_tips)
                    
                    error_msg += "\n\n💡 General Tips:\n"
                    error_msg += "  - Fix syntax errors in the source code\n"
                    error_msg += "  - Ensure all referenced objects are activated\n"
                    error_msg += "  - Use activate_multiple_objects() to activate dependent objects together\n"
                    error_msg += "  - Check object source with get_object_source() to view the code"
                    
                    raise Exception(error_msg)
                
                # Success - no errors found
                logger.info(f"Activation run {run_id} completed successfully - all {len(objects)} objects activated")
                return {
                    'status': 'finished',
                    'progress': progress,
                    'result_kind': result_kind,
                    'run_id': run_id,
                    'result_xml': result_response.text,
                    'objects_count': len(objects),
                    'success': True
                }
            
            except Exception as e:
                # If we can't fetch the result, log warning and return success based on status
                error_msg = str(e)
                if "Activation run completed but" in error_msg:
                    # Re-raise our own activation error exceptions
                    raise
                else:
                    # Log error fetching result but don't fail the activation
                    logger.warning(f"Could not fetch activation result details: {error_msg}")
                    return {
                        'status': 'finished',
                        'progress': progress,
                        'result_kind': result_kind,
                        'run_id': run_id,
                        'objects_count': len(objects),
                        'verified': False
                    }
        
        elif status == 'failed':
            raise Exception(f"Activation run failed. Run ID: {run_id}")
        
        elif status == 'cancelled':
            logger.warning(f"Activation run {run_id} was cancelled")
            raise Exception(f"Activation run was cancelled. Run ID: {run_id}. Please try activating the objects again.")
        
        # Still running, wait before next poll
        if attempt < max_poll_attempts - 1:
            time.sleep(poll_interval)
    
    # Timeout reached
    raise Exception(
        f"Activation run did not complete within {max_poll_attempts * poll_interval} seconds. "
        f"Run ID: {run_id}, Last status: {status}, Progress: {progress}%"
    )
