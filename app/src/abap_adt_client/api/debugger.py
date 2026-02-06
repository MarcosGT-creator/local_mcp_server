"""ABAP Debugger API - ADT endpoint wrappers for debugging ABAP programs.

This module provides programmatic access to SAP's ABAP Debugger through ADT endpoints.
It allows attaching to debug sessions, managing breakpoints, inspecting variables,
and controlling step execution.

Note: Debug sessions must be initiated by a human developer in Eclipse ADT or by
running an ABAP program in debug mode on SAP. These APIs allow you to control
existing debug sessions programmatically.
"""

from typing import List, Dict, Optional, Literal, TypedDict, Any, Union
from ..http_request import HttpRequestParameters, request
import xml.etree.ElementTree as ET


# Type definitions
DebuggingMode = Literal["user", "terminal"]
DebugStepType = Literal[
    "stepInto", "stepOver", "stepReturn", "stepContinue", 
    "stepRunToLine", "stepJumpToLine", "terminateDebuggee"
]
DebuggerScope = Literal["external", "debugger"]
DebugMetaTypeSimple = Literal["simple", "string", "boxedcomp", "anonymcomp", "unknown"]
DebugMetaTypeComplex = Literal[
    "structure", "table", "dataref", "objectref", "class", "object", "boxref"
]


class DebugMessage(TypedDict):
    """Debug message with text and language."""
    text: str
    lang: str


class DebugListenerError(TypedDict):
    """Error returned from debug listener."""
    namespace: str
    type: str
    message: DebugMessage
    localizedMessage: DebugMessage
    conflictText: str
    ideUser: str
    subType: str
    t100KeyId: str
    t100KeyNo: int


class Debuggee(TypedDict):
    """Information about a debuggee (running ABAP program being debugged)."""
    CLIENT: int
    DEBUGGEE_ID: str
    TERMINAL_ID: str
    IDE_ID: str
    DEBUGGEE_USER: str
    PRG_CURR: str  # Current program name
    INCL_CURR: str  # Current include name
    LINE_CURR: int  # Current line number
    RFCDEST: str
    APPLSERVER: str
    SYSID: str
    SYSNR: int
    DBGKEY: str
    TSTMP: int
    DBGEE_KIND: str
    URI: str


class DebugVariable(TypedDict):
    """Debug variable information."""
    ID: str
    NAME: str
    DECLARED_TYPE_NAME: str
    ACTUAL_TYPE_NAME: str
    KIND: str
    INSTANTIATION_KIND: str
    ACCESS_KIND: str
    META_TYPE: str
    PARAMETER_KIND: str
    VALUE: str
    HEX_VALUE: str
    READ_ONLY: str
    TECHNICAL_TYPE: str
    LENGTH: int
    TABLE_BODY: str
    TABLE_LINES: int
    IS_VALUE_INCOMPLETE: str
    IS_EXCEPTION: str
    INHERITANCE_LEVEL: int
    INHERITANCE_CLASS: str


class DebugBreakpoint(TypedDict, total=False):
    """Debug breakpoint definition."""
    id: str
    kind: str  # "line", "statement", etc.
    clientId: str
    uri: str
    line: int
    condition: Optional[str]
    enabled: bool
    skipCount: int


class DebugStackEntry(TypedDict):
    """Call stack entry."""
    level: int
    type: str
    name: str
    include: str
    line: int
    uri: str


class DebugSettings(TypedDict, total=False):
    """Debugger settings."""
    breakAtStart: bool
    breakAtEnd: bool
    breakAtStaticError: bool
    breakAtDynamicError: bool
    breakAtCheckpoint: bool
    breakAtAssert: bool
    breakAtRFCCall: bool
    breakAtNewProcess: bool
    ignoreOwnCode: bool
    systemDebugging: bool
    createExceptionObject: bool
    backgroundRFC: bool
    sharedObjectDebugging: bool
    showDataAging: bool
    updateDebugging: bool


class DebugAttach(TypedDict):
    """Response from attaching to a debuggee."""
    debuggeeId: str
    status: str
    reachedBreakpoints: List[Dict[str, str]]
    actions: List[Dict[str, str]]


class DebugStep(TypedDict):
    """Response from a step operation."""
    status: str
    stopReason: str
    actions: List[Dict[str, str]]
    settings: Dict[str, str]


def _parse_xml_to_dict(xml_text: str) -> ET.Element:
    """Parse XML response to ET.Element."""
    root = ET.fromstring(xml_text)
    # Remove namespace prefixes for easier parsing
    for elem in root.iter():
        if '}' in elem.tag:
            elem.tag = elem.tag.split('}', 1)[1]
    return root


def _xml_node_attr(node: ET.Element) -> Dict[str, Any]:
    """Extract attributes from XML node."""
    result: Dict[str, Any] = {}
    for child in node:
        tag = child.tag.split('}')[-1]  # Remove namespace
        result[tag] = child.text or ''
    result.update(node.attrib)
    return result


def debugger_listeners(
    http_request_parameters: HttpRequestParameters,
    debugging_mode: DebuggingMode,
    terminal_id: str,
    ide_id: str,
    request_user: Optional[str] = None,
    check_conflict: bool = True
) -> Optional[Union[Debuggee, DebugListenerError]]:
    """Check for active debugging sessions and manage debuggee connections.
    
    This function queries the SAP system for active debug sessions that match
    the specified terminal and IDE identifiers. It's used to discover if there
    are any programs waiting to be debugged or already being debugged.
    
    Args:
        http_request_parameters: HTTP request parameters
        debugging_mode: "user" or "terminal" debugging mode
        terminal_id: Terminal identifier (unique per terminal session)
        ide_id: IDE identifier (unique per IDE instance)
        request_user: Optional SAP username filter
        check_conflict: Check for conflicting debug sessions
        
    Returns:
        Debuggee object if a debuggee is found, DebugListenerError if error,
        or None if no debuggees found
        
    Example:
        >>> result = debugger_listeners(
        ...     params, "user", "TERM123", "IDE456", "DEVELOPER01"
        ... )
        >>> if result and 'DEBUGGEE_ID' in result:
        ...     print(f"Found debuggee: {result['PRG_CURR']} at line {result['LINE_CURR']}")
    """
    params = {
        "debuggingMode": debugging_mode,
        "terminalId": terminal_id,
        "ideId": ide_id,
        "checkConflict": str(check_conflict).lower()
    }
    if request_user:
        params["requestUser"] = request_user
    
    response = request(
        http_request_parameters=http_request_parameters,
        uri="/sap/bc/adt/debugger/listeners",
        method="GET",
        body="",
        params=params,
        accept="application/xml"
    )
    
    if not response.text:
        return None
        
    try:
        root = _parse_xml_to_dict(response.text)
        # Check for error first
        exception = root.find('.//exception')
        if exception is not None:
            # Parse error
            error_dict = _xml_node_attr(exception)
            return error_dict  # type: ignore
        
        # Parse debuggee
        data = root.find('.//DATA')
        if data is not None:
            debuggee = {}
            for child in data:
                tag = child.tag.split('}')[-1]
                if tag in ['CLIENT', 'SYSNR', 'LINE_CURR', 'TSTMP', 'TABLE_LINES']:
                    debuggee[tag] = int(child.text or 0)
                else:
                    debuggee[tag] = child.text or ''
            return debuggee  # type: ignore
    except Exception as e:
        raise Exception(f"Failed to parse debugger listeners response: {e}\n{response.text}")
    
    return None


def debugger_attach(
    http_request_parameters: HttpRequestParameters,
    debugging_mode: DebuggingMode,
    debuggee_id: str,
    request_user: str = "",
    dynpro_debugging: bool = True
) -> DebugAttach:
    """Attach to a running ABAP program for debugging.
    
    After discovering a debuggee using debugger_listeners(), use this function
    to attach the debugger to it. This establishes a debugging session where
    you can set breakpoints, inspect variables, and step through code.
    
    Args:
        http_request_parameters: HTTP request parameters
        debugging_mode: "user" or "terminal" debugging mode
        debuggee_id: ID of the debuggee to attach to (from debugger_listeners)
        request_user: SAP username requesting the debug session
        dynpro_debugging: Enable dynpro (screen) debugging
        
    Returns:
        DebugAttach object with attachment status and available actions
        
    Example:
        >>> attach_result = debugger_attach(
        ...     params, "user", "D2A_123456", "DEVELOPER01"
        ... )
        >>> print(f"Attached: {attach_result['status']}")
    """
    params = {
        "method": "attach",
        "debuggeeId": debuggee_id,
        "dynproDebugging": str(dynpro_debugging).lower(),
        "debuggingMode": debugging_mode,
        "requestUser": request_user
    }
    
    response = request(
        http_request_parameters=http_request_parameters,
        uri="/sap/bc/adt/debugger",
        method="POST",
        body="",
        params=params,
        accept="application/xml"
    )
    
    root = _parse_xml_to_dict(response.text)
    result = _xml_node_attr(root)
    
    # Parse reachedBreakpoints
    reached = []
    for bp in root.findall('.//reachedBreakpoint'):
        reached.append(_xml_node_attr(bp))
    result['reachedBreakpoints'] = reached
    
    # Parse actions
    actions = []
    for action in root.findall('.//action'):
        actions.append(_xml_node_attr(action))
    result['actions'] = actions
    
    return result  # type: ignore


def debugger_set_breakpoints(
    http_request_parameters: HttpRequestParameters,
    debugging_mode: DebuggingMode,
    terminal_id: str,
    ide_id: str,
    client_id: str,
    breakpoints: List[DebugBreakpoint],
    request_user: Optional[str] = None,
    scope: DebuggerScope = "external",
    system_debugging: bool = False,
    deactivated: bool = False
) -> List[DebugBreakpoint]:
    """Set breakpoints in ABAP code.
    
    Configure line breakpoints with optional conditions. Breakpoints can be set
    before or after attaching to a debuggee.
    
    Args:
        http_request_parameters: HTTP request parameters
        debugging_mode: "user" or "terminal" debugging mode
        terminal_id: Terminal identifier
        ide_id: IDE identifier
        client_id: Client identifier for breakpoints
        breakpoints: List of breakpoint definitions
        request_user: SAP username
        scope: "external" or "debugger" scope
        system_debugging: Enable system debugging
        deactivated: Set breakpoints as deactivated
        
    Returns:
        List of created/updated breakpoints with IDs
        
    Example:
        >>> breakpoints = [{
        ...     "kind": "line",
        ...     "clientId": "VSCode",
        ...     "uri": "/sap/bc/adt/programs/programs/z_test#start=10",
        ...     "line": 10,
        ...     "condition": "lv_count > 5"
        ... }]
        >>> result = debugger_set_breakpoints(
        ...     params, "user", "TERM123", "IDE456", "VSCode", breakpoints
        ... )
    """
    # Format breakpoints as XML
    bp_xml = []
    for bp in breakpoints:
        uri_attr = f'adtcore:uri="{bp["uri"]}"' if "uri" in bp else ''
        condition_attr = f'condition="{bp.get("condition", "")}"' if bp.get("condition") else ''
        bp_xml.append(
            f'<breakpoint xmlns:adtcore="http://www.sap.com/adt/core" '
            f'kind="{bp.get("kind", "line")}" '
            f'clientId="{client_id}" '
            f'skipCount="{bp.get("skipCount", 0)}" '
            f'{uri_attr} {condition_attr}/>'
        )
    
    body = f"""<?xml version="1.0" encoding="UTF-8"?>
        <dbg:breakpoints scope="{scope}" debuggingMode="{debugging_mode}"
            requestUser="{request_user or ''}" terminalId="{terminal_id}" ideId="{ide_id}"
            systemDebugging="{str(system_debugging).lower()}" deactivated="{str(deactivated).lower()}"
            xmlns:dbg="http://www.sap.com/adt/debugger">
            <syncScope mode="full"></syncScope>
            {''.join(bp_xml)}
        </dbg:breakpoints>"""
    
    response = request(
        http_request_parameters=http_request_parameters,
        uri="/sap/bc/adt/debugger/breakpoints",
        method="POST",
        body=body,
        params={},
        content_type="application/xml",
        accept="application/xml"
    )
    
    # Parse response
    root = _parse_xml_to_dict(response.text)
    result_breakpoints = []
    for bp in root.findall('.//breakpoint'):
        result_breakpoints.append(_xml_node_attr(bp))
    
    return result_breakpoints  # type: ignore


def debugger_delete_breakpoint(
    http_request_parameters: HttpRequestParameters,
    breakpoint_id: str,
    debugging_mode: DebuggingMode,
    terminal_id: str,
    ide_id: str,
    request_user: Optional[str] = None,
    scope: DebuggerScope = "external"
) -> bool:
    """Delete a specific breakpoint.
    
    Args:
        http_request_parameters: HTTP request parameters
        breakpoint_id: ID of the breakpoint to delete
        debugging_mode: "user" or "terminal" debugging mode
        terminal_id: Terminal identifier
        ide_id: IDE identifier
        request_user: SAP username
        scope: "external" or "debugger" scope
        
    Returns:
        True if successful
    """
    from urllib.parse import quote
    
    params = {
        "scope": scope,
        "debuggingMode": debugging_mode,
        "terminalId": terminal_id,
        "ideId": ide_id
    }
    if request_user:
        params["requestUser"] = request_user
    
    response = request(
        http_request_parameters=http_request_parameters,
        uri=f"/sap/bc/adt/debugger/breakpoints/{quote(breakpoint_id)}",
        method="DELETE",
        body="",
        params=params,
        accept="application/xml"
    )
    
    return response.status_code in [200, 204]


def debugger_step(
    http_request_parameters: HttpRequestParameters,
    method: DebugStepType,
    uri: Optional[str] = None
) -> DebugStep:
    """Execute a step operation in the debugger.
    
    Control the execution flow of the debugged program.
    
    Args:
        http_request_parameters: HTTP request parameters
        method: Step type - "stepInto", "stepOver", "stepReturn", "stepContinue", etc.
        uri: Optional URI for stepRunToLine or stepJumpToLine
        
    Returns:
        DebugStep object with execution status
        
    Example:
        >>> # Step over current line
        >>> result = debugger_step(params, "stepOver")
        >>> print(f"Stopped at: {result['stopReason']}")
        >>>
        >>> # Continue execution
        >>> result = debugger_step(params, "stepContinue")
    """
    params = {"method": method}
    if uri:
        params["uri"] = uri
    
    response = request(
        http_request_parameters=http_request_parameters,
        uri="/sap/bc/adt/debugger",
        method="POST",
        body="",
        params=params,
        accept="application/xml"
    )
    
    root = _parse_xml_to_dict(response.text)
    result = _xml_node_attr(root)
    
    # Parse settings
    settings_node = root.find('.//settings')
    if settings_node is not None:
        result['settings'] = _xml_node_attr(settings_node)
    
    # Parse actions
    actions = []
    for action in root.findall('.//action'):
        actions.append(_xml_node_attr(action))
    result['actions'] = actions
    
    return result  # type: ignore


def debugger_stack(
    http_request_parameters: HttpRequestParameters,
    semantic_uris: bool = True
) -> Dict[str, Any]:
    """Get the current call stack.
    
    Retrieve the call stack showing the sequence of program calls that led
    to the current execution point.
    
    Args:
        http_request_parameters: HTTP request parameters
        semantic_uris: Use semantic URIs for stack entries
        
    Returns:
        Dictionary with call stack information
        
    Example:
        >>> stack = debugger_stack(params)
        >>> for entry in stack['stack']:
        ...     print(f"Level {entry['level']}: {entry['name']} line {entry['line']}")
    """
    params = {
        "method": "getStack",
        "emode": "_",
        "semanticURIs": str(semantic_uris).lower()
    }
    
    response = request(
        http_request_parameters=http_request_parameters,
        uri="/sap/bc/adt/debugger/stack",
        method="GET",
        body="",
        params=params,
        accept="application/xml"
    )
    
    root = _parse_xml_to_dict(response.text)
    result = _xml_node_attr(root)
    
    # Parse stack entries
    stack = []
    for entry in root.findall('.//stackEntry'):
        stack_entry = _xml_node_attr(entry)
        stack.append(stack_entry)
    result['stack'] = stack
    
    return result


def debugger_variables(
    http_request_parameters: HttpRequestParameters,
    variable_ids: List[str]
) -> List[DebugVariable]:
    """Get variable values by their IDs.
    
    Retrieve detailed information about specific variables including their
    values, types, and metadata.
    
    Args:
        http_request_parameters: HTTP request parameters
        variable_ids: List of variable IDs to retrieve
        
    Returns:
        List of DebugVariable objects with variable details
        
    Example:
        >>> variables = debugger_variables(params, ["@ROOT", "LV_COUNT"])
        >>> for var in variables:
        ...     print(f"{var['NAME']}: {var['VALUE']} ({var['DECLARED_TYPE_NAME']})")
    """
    # Format variables as XML
    vars_xml = ''.join([
        f'<STPDA_ADT_VARIABLE><ID>{var_id}</ID></STPDA_ADT_VARIABLE>'
        for var_id in variable_ids
    ])
    
    body = f"""<?xml version="1.0" encoding="UTF-8" ?>
<asx:abap xmlns:asx="http://www.sap.com/abapxml" version="1.0">
<asx:values>
    <DATA>{vars_xml}</DATA>
</asx:values>
</asx:abap>"""
    
    response = request(
        http_request_parameters=http_request_parameters,
        uri="/sap/bc/adt/debugger",
        method="POST",
        body=body,
        params={"method": "getVariables"},
        content_type="application/vnd.sap.as+xml; charset=UTF-8; dataname=com.sap.adt.debugger.Variables",
        accept="application/vnd.sap.as+xml;charset=UTF-8;dataname=com.sap.adt.debugger.Variables"
    )
    
    # Parse response
    root = _parse_xml_to_dict(response.text)
    variables = []
    for var in root.findall('.//STPDA_ADT_VARIABLE'):
        var_dict = {}
        for child in var:
            tag = child.tag.split('}')[-1]
            if tag in ['LENGTH', 'TABLE_LINES', 'INHERITANCE_LEVEL']:
                var_dict[tag] = int(child.text or 0)
            else:
                var_dict[tag] = child.text or ''
        variables.append(var_dict)
    
    return variables  # type: ignore


def debugger_child_variables(
    http_request_parameters: HttpRequestParameters,
    parent_ids: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Get child variables for complex types (structures, tables, objects).
    
    For variables of complex types, retrieve their child/nested variables.
    
    Args:
        http_request_parameters: HTTP request parameters
        parent_ids: List of parent variable IDs (default: ["@ROOT", "@DATAAGING"])
        
    Returns:
        Dictionary with hierarchies and child variables
        
    Example:
        >>> children = debugger_child_variables(params, ["@ROOT"])
        >>> for var in children['variables']:
        ...     print(f"{var['NAME']}: {var['VALUE']}")
    """
    if parent_ids is None:
        parent_ids = ["@ROOT", "@DATAAGING"]
    
    # Format hierarchies as XML
    hierarchies_xml = ''.join([
        f'<STPDA_ADT_VARIABLE_HIERARCHY><PARENT_ID>{parent_id}</PARENT_ID></STPDA_ADT_VARIABLE_HIERARCHY>'
        for parent_id in parent_ids
    ])
    
    body = f"""<?xml version="1.0" encoding="UTF-8" ?>
<asx:abap version="1.0" xmlns:asx="http://www.sap.com/abapxml">
<asx:values>
<DATA>
    <HIERARCHIES>{hierarchies_xml}</HIERARCHIES>
</DATA>
</asx:values>
</asx:abap>"""
    
    response = request(
        http_request_parameters=http_request_parameters,
        uri="/sap/bc/adt/debugger",
        method="POST",
        body=body,
        params={"method": "getChildVariables"},
        content_type="application/vnd.sap.as+xml; charset=UTF-8; dataname=com.sap.adt.debugger.ChildVariables",
        accept="application/vnd.sap.as+xml;charset=UTF-8;dataname=com.sap.adt.debugger.ChildVariables"
    )
    
    # Parse response
    root = _parse_xml_to_dict(response.text)
    
    # Parse hierarchies
    hierarchies = []
    for hier in root.findall('.//STPDA_ADT_VARIABLE_HIERARCHY'):
        hierarchies.append(_xml_node_attr(hier))
    
    # Parse variables
    variables = []
    for var in root.findall('.//STPDA_ADT_VARIABLE'):
        var_dict = {}
        for child in var:
            tag = child.tag.split('}')[-1]
            if tag in ['LENGTH', 'TABLE_LINES', 'INHERITANCE_LEVEL']:
                var_dict[tag] = int(child.text or 0)
            else:
                var_dict[tag] = child.text or ''
        variables.append(var_dict)
    
    return {
        'hierarchies': hierarchies,
        'variables': variables
    }


def debugger_set_variable_value(
    http_request_parameters: HttpRequestParameters,
    variable_name: str,
    value: str
) -> str:
    """Set the value of a variable during debugging.
    
    Modify a variable's value at runtime. Useful for testing different
    execution paths or fixing issues during debugging.
    
    Args:
        http_request_parameters: HTTP request parameters
        variable_name: Name of the variable to modify
        value: New value to set
        
    Returns:
        Response body from the operation
        
    Example:
        >>> result = debugger_set_variable_value(params, "LV_COUNT", "10")
    """
    params = {
        "method": "setVariableValue",
        "variableName": variable_name
    }
    
    response = request(
        http_request_parameters=http_request_parameters,
        uri="/sap/bc/adt/debugger",
        method="POST",
        body=value,
        params=params,
        content_type="text/plain"
    )
    
    return response.text


def debugger_save_settings(
    http_request_parameters: HttpRequestParameters,
    settings: DebugSettings
) -> DebugSettings:
    """Save debugger settings.
    
    Configure global debugger behavior such as when to break (at errors,
    checkpoints, asserts, etc.).
    
    Args:
        http_request_parameters: HTTP request parameters
        settings: Debugger settings to apply
        
    Returns:
        Updated debugger settings
        
    Example:
        >>> settings = {
        ...     "breakAtStart": False,
        ...     "breakAtStaticError": True,
        ...     "breakAtDynamicError": True,
        ...     "breakAtCheckpoint": True
        ... }
        >>> result = debugger_save_settings(params, settings)
    """
    # Convert boolean settings to lowercase strings
    settings_attrs = ' '.join([
        f'{key}="{str(value).lower()}"'
        for key, value in settings.items()
    ])
    
    body = f"""<?xml version="1.0" encoding="UTF-8"?>
<dbg:settings xmlns:dbg="http://www.sap.com/adt/debugger" {settings_attrs}>
</dbg:settings>"""
    
    response = request(
        http_request_parameters=http_request_parameters,
        uri="/sap/bc/adt/debugger",
        method="POST",
        body=body,
        params={"method": "setDebuggerSettings"},
        content_type="application/xml",
        accept="application/xml"
    )
    
    root = _parse_xml_to_dict(response.text)
    return _xml_node_attr(root)  # type: ignore


def debugger_go_to_stack(
    http_request_parameters: HttpRequestParameters,
    stack_uri: str
) -> bool:
    """Navigate to a specific stack level.
    
    Jump to a different level in the call stack to inspect that context.
    
    Args:
        http_request_parameters: HTTP request parameters
        stack_uri: URI of the stack level (format: /sap/bc/adt/debugger/stack/type/{type}/position/{pos})
        
    Returns:
        True if successful
        
    Example:
        >>> # Navigate to stack position 2
        >>> uri = "/sap/bc/adt/debugger/stack/type/ABAP/position/2"
        >>> debugger_go_to_stack(params, uri)
    """
    import re
    if not re.match(r'^/sap/bc/adt/debugger/stack/type/[\w]+/position/\d+$', stack_uri):
        raise ValueError(f"Invalid stack URI format: {stack_uri}")
    
    response = request(
        http_request_parameters=http_request_parameters,
        uri=stack_uri,
        method="PUT",
        body="",
        params={}
    )
    
    return response.status_code in [200, 204]
