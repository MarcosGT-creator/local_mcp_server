import requests
from requests.auth import AuthBase
from typing import Any, Dict, List, Literal, Optional, Union
import base64

from .api.syntax import SyntaxCheckResult, syntax_check
from .api.objectstructure import object_structure
from .api.prettyprint import (
    PrettyPrintSettings,
    prettyprint,
    set_pretty_printer_settings,
)
from .api.create import create, create_test_class_include, ObjectTypes
from .api.activate import activate, get_inactive_objects, activate_multiple_objects
from .api.service_binding import ServiceBindingVersion
from .api.delete import delete
from .api.lock import lock, unlock, LockResult
from .api.changepackage import change_package
from .api.login import login
from .api.content import get_object_source, set_object_source
from .api.search import search_object
from .api.virtualfolders import get_package_contents
from .api.unittest import UnittestFlags, run_unit_test
from .api.transportcheck import transport_check, TransportCheckResult
from .api.createtransport import (
    create_transport,
    create_transport_organizer,
    CreateTransportResult,
    TransportOrganizerResult,
)
from .api.listtransports import list_transports, ListTransportsResult
from .api.objecttypes import get_searchable_object_types
from .api.odata import get_odata_metadata, call_odata_service
from .api.datapreview import get_ddic_metadata, preview_ddic_data
from .api.ddic_types import DDIC_OBJECT_TYPES
from .api.debugger import (
    DebuggingMode,
    DebugStepType,
    DebuggerScope,
    Debuggee,
    DebugListenerError,
    DebugVariable,
    DebugBreakpoint,
    DebugStackEntry,
    DebugSettings,
    DebugAttach,
    DebugStep,
    debugger_listeners,
    debugger_attach,
    debugger_set_breakpoints,
    debugger_delete_breakpoint,
    debugger_step,
    debugger_stack,
    debugger_variables,
    debugger_child_variables,
    debugger_set_variable_value,
    debugger_save_settings,
    debugger_go_to_stack,
)
from .api.service_binding import (
    ServiceBindingVersion,
    ServiceBindingPublishStatus,
    create_service_binding,
    publish_service_binding,
    unpublish_service_binding,
    get_binding_types,
)
from .http_request import HttpRequestParameters


class PreEncodedBasicAuth(AuthBase):
    """Custom auth handler that uses a pre-encoded Basic Auth token.

    This allows clients to send pre-computed base64-encoded credentials
    without exposing raw passwords to the server.
    """

    def __init__(self, encoded_credentials: str):
        """
        Args:
            encoded_credentials: Base64-encoded "username:password" string
                                (without "Basic " prefix)
        """
        self.encoded_credentials = encoded_credentials

    def __call__(self, r):
        r.headers["Authorization"] = f"Basic {self.encoded_credentials}"
        return r


class AdtClient:
    def __init__(
        self,
        sap_host: str,
        username: str,
        password: str,
        client: str = "110",
    ):
        """Initialize ADT Client with username and password.

        Args:
            sap_host: SAP system URL
            username: SAP username
            password: SAP password (not logged or stored)
            client: SAP client number (default: 110)

        Examples:
            >>> client = AdtClient(
            ...     sap_host="https://sap.com",
            ...     username="myuser",
            ...     password="mypass",
            ...     client="110"
            ... )

        Raises:
            ValueError: If username or password is not provided
        """
        if not username or not password:
            raise ValueError("username and password are required.")

        self.sap_host = sap_host
        self.client = client
        self.username = username
        
        # Generate auth token from username and password
        basic_auth_token = base64.b64encode(f"{username}:{password}".encode()).decode()
        self._basic_auth_token = basic_auth_token  # Store for credential comparison
        
        self.csrf_token: str = "fetch"
        self.request_number: int = 0
        self.statefulness: Literal["stateless", "stateful"] = "stateless"
        self.session = requests.Session()
        self.session.verify = False

        # Set up authentication with pre-encoded token
        self.session.auth = PreEncodedBasicAuth(basic_auth_token)

    def build_request_parameters(self) -> HttpRequestParameters:
        http_request_parameters: HttpRequestParameters = {
            "host": self.sap_host,
            "csrf_token": self.csrf_token,
            "statefulness": self.statefulness,
            "request_number": self.request_number,
            "session": self.session,
            "client": self.client,
        }
        self.request_number += 1
        return http_request_parameters

    def login(self) -> bool:
        http_request_parameters = self.build_request_parameters()
        csrf_token = login(http_request_parameters)
        if csrf_token:
            self.csrf_token = csrf_token
            return True
        else:
            raise Exception("Login failed.")

    def search_object(
        self, query: str, max_results: int = 1, object_type: Optional[str] = None
    ) -> List[Dict[str, str]]:
        http_request_parameters = self.build_request_parameters()
        elements = search_object(
            http_request_parameters, query, max_results, object_type
        )
        return elements

    def get_package_objects(
        self,
        package_name: str,
        object_search_pattern: str = "*",
        group_filter: Optional[str] = None,
        type_filter: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        """
        Fetch objects from a package using the virtual folders API.
        
        Args:
            package_name: Name of the package (e.g., "ZGET_SUBS_API")
            object_search_pattern: Pattern for object names (default: "*")
            group_filter: Optional group filter (e.g., "CORE_DATA_SERVICES", "SOURCE_LIBRARY")
            type_filter: Optional type filter (e.g., "DDLS", "CLAS", "PROG")
        
        Returns:
            List of folders or objects from the package
        """
        from .response_parsing import parse_virtual_folders_result
        
        http_request_parameters = self.build_request_parameters()
        xml_response = get_package_contents(
            http_request_parameters,
            package_name,
            object_search_pattern,
            group_filter,
            type_filter,
        )
        return parse_virtual_folders_result(xml_response)

    def get_object_source(
        self,
        object_uri: str,
        version: Literal["active", "inactive", "workingArea"] = "active",
    ) -> str:
        http_request_parameters = self.build_request_parameters()
        response = get_object_source(http_request_parameters, object_uri, version)
        return response

    def activate(self, object_name: str, object_uri: str) -> bool:
        http_request_parameters = self.build_request_parameters()
        response = activate(http_request_parameters, object_name, object_uri)
        return response

    def get_inactive_objects(self) -> List[Dict[str, Any]]:
        """
        Get list of inactive objects for the current user.
        
        Returns:
            List of inactive objects with their URIs, names, types, and transport info
        """
        http_request_parameters = self.build_request_parameters()
        return get_inactive_objects(http_request_parameters)

    def activate_multiple_objects(
        self,
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
            objects: List of dicts with 'uri' and 'name' keys for each object
            preaudit_requested: Whether to request pre-activation audit (default: False)
            max_poll_attempts: Maximum number of polling attempts (default: 60)
            poll_interval: Seconds between poll attempts (default: 2)
        
        Returns:
            Dict with activation result including status and any messages
        """
        http_request_parameters = self.build_request_parameters()
        return activate_multiple_objects(
            http_request_parameters,
            objects,
            preaudit_requested,
            max_poll_attempts,
            poll_interval
        )

    def lock(self, object_uri: str) -> LockResult:
        """Lock an SAP object for editing.

        Returns a dictionary with lock information including the lock handle
        and transport request details if the object is already in a transport.

        Args:
            object_uri: URI of the object to lock

        Returns:
            LockResult dictionary with LOCK_HANDLE and transport info
        """
        self.statefulness = "stateful"
        http_request_parameters = self.build_request_parameters()
        response = lock(http_request_parameters, object_uri)
        return response

    def unlock(self, object_uri: str, lock_handle: str) -> bool:
        http_request_parameters = self.build_request_parameters()
        response = unlock(http_request_parameters, object_uri, lock_handle)
        self.statefulness = "stateless"
        return response

    def change_package(
        self,
        object_uri: str,
        object_name: str,
        object_type: str,
        old_package: str,
        new_package: str,
        transport_number: str
    ) -> Dict[str, Any]:
        """
        Change the package assignment of an SAP object.
        
        Moves objects between packages (typically from $TMP to transportable packages)
        and assigns them to a transport request in one operation.
        
        Args:
            object_uri: URI of the object
            object_name: Name of the object
            object_type: Type of object (e.g., DDLS/DF)
            old_package: Current package
            new_package: Target package
            transport_number: Transport request number
        
        Returns:
            Dict with success status and details
        """
        http_request_parameters = self.build_request_parameters()
        return change_package(
            http_request_parameters,
            object_uri,
            object_name,
            object_type,
            old_package,
            new_package,
            transport_number
        )

    def set_object_source(
        self,
        object_uri: str,
        source_code: str,
        lock_handle: str,
        corr_nr: str | None = None,
    ) -> bool:
        http_request_parameters = self.build_request_parameters()
        response = set_object_source(
            http_request_parameters, object_uri, source_code, lock_handle, corr_nr
        )
        return response

    def run_unit_test(
        self,
        object_uri: str,
        unit_test_flags: UnittestFlags = UnittestFlags(),
        # ) -> List[UnitTestAlert]:
    ) -> str:
        http_request_parameters = self.build_request_parameters()
        response = run_unit_test(http_request_parameters, object_uri, unit_test_flags)
        return response

    def delete(self, object_uri: str, lock_handle: str) -> bool:
        http_request_parameters = self.build_request_parameters()
        response = delete(http_request_parameters, object_uri, lock_handle)
        return response

    def create(
        self, object_type: ObjectTypes, name: str, parent: str, description: str, corr_nr: str = ""
    ) -> bool:
        http_request_parameters = self.build_request_parameters()
        response = create(
            http_request_parameters,
            object_type,
            name,
            parent,
            description,
            self.username,
            corr_nr,
        )
        return response

    def create_test_class_include(self, class_name: str, lock_handle: str) -> bool:
        http_request_parameters = self.build_request_parameters()
        response = create_test_class_include(
            http_request_parameters, class_name, lock_handle
        )
        return response

    def prettyprint(self, src: str) -> str:
        http_request_parameters = self.build_request_parameters()
        response = prettyprint(http_request_parameters, src)
        return response

    def prettyprint_settings(self, settings: PrettyPrintSettings) -> bool:
        http_request_parameters = self.build_request_parameters()
        response = set_pretty_printer_settings(http_request_parameters, settings)
        return response

    def syntax_check(
        self,
        object_uri: str,
        include_uri: str,
        src: str,
        version: Literal["active", "inactive"] = "active",
    ) -> List[SyntaxCheckResult]:
        http_request_parameters = self.build_request_parameters()
        response = syntax_check(
            http_request_parameters, object_uri, include_uri, src, version
        )
        return response

    def object_structure(self, object_uri: str):
        http_request_parameters = self.build_request_parameters()
        response = object_structure(http_request_parameters, object_uri)
        return response

    def transport_check(self, object_uri: str) -> TransportCheckResult:
        """Perform a transport check for an SAP object.

        Returns structured data with available transport requests and object metadata.
        The SAP system automatically determines PGMID, OBJECT, OBJECTNAME, and
        DEVCLASS from the URI.

        This is used when an object is NOT yet locked in a transport. The returned
        list of transport requests allows the LLM/user to select which transport
        to use for the object modification.

        Args:
            object_uri: URI of the object to check (e.g., /sap/bc/adt/oo/classes/zcl_test/source/main)

        Returns:
            TransportCheckResult with object metadata and list of available transport requests

        Example:
            >>> result = client.transport_check("/sap/bc/adt/oo/classes/zcl_test/source/main")
            >>> print(f"Package: {result['DEVCLASS']}")
            >>> for req in result['REQUESTS']:
            ...     print(f"{req['TRKORR']}: {req['AS4TEXT']}")
        """
        http_request_parameters = self.build_request_parameters()
        response = transport_check(http_request_parameters, object_uri)
        return response

    def create_transport_and_assign(
        self,
        devclass: str,
        request_text: str,
        ref: str,
        operation: str = "",
    ) -> CreateTransportResult:
        """Create a new transport request and assign an object to it.

        Creates a new workbench transport request for transporting object
        modifications. This is typically called after transport_check() when
        the user wants to create a new transport instead of using an existing one.

        Args:
            devclass: Development class/package (e.g., ZSAP_LLM_API)
            request_text: Description for the transport (e.g., "Bug fix for API")
            ref: Reference URI of the object (e.g., /sap/bc/adt/oo/classes/zcl_test/source/main)
            operation: Operation type (optional, usually empty)

        Returns:
            CreateTransportResult with the new TRKORR (transport number) and any messages

        Example:
            >>> result = client.create_transport(
            ...     devclass="ZSAP_LLM_API",
            ...     request_text="Fix bug in API class",
            ...     ref="/sap/bc/adt/oo/classes/zcl_api/source/main"
            ... )
            >>> print(f"Created transport: {result['TRKORR']}")
        """
        http_request_parameters = self.build_request_parameters()
        response = create_transport(
            http_request_parameters, devclass, request_text, ref, operation
        )
        return response

    def create_transport_organizer(
        self,
        description: str,
        target: str = "",
        tr_type: Literal["K", "W"] = "K",
        owner: str = "",
    ) -> TransportOrganizerResult:
        """Create a new transport request via Transport Organizer (pure/generic).

        This is a simpler, standalone transport creation API that's NOT tied
        to a specific object. Use this when creating a transport independently.

        Args:
            description: Transport description (e.g., "API bug fixes")
            target: Target system (default: "/ZNQUALIT/", use "/ZPRD/" for production)
            tr_type: "K" for Workbench (default), "W" for Customizing
            owner: Task owner (optional, defaults to current user)

        Returns:
            TransportOrganizerResult with TRKORR and transport details

        Example:
            >>> result = client.create_transport_organizer(
            ...     description="Bug fixes for SAP API",
            ...     target="/ZNQUALIT/"
            ... )
            >>> print(f"Created transport: {result['TRKORR']}")

        Note:
            This is the cleaner API for creating transports independently.
            Use create_transport() when creating a transport tied to a specific object.
        """
        
        # For populating owner if not provided
        # SAP usernames are always uppercase
        owner = (owner or self.username).upper()
        
        http_request_parameters = self.build_request_parameters()
        response = create_transport_organizer(
            http_request_parameters, description, target, tr_type, owner
        )
        return response

    def list_transports(
        self,
        targets: bool = True,
        transport_number: Optional[str] = None,
    ) -> ListTransportsResult:
        """List transport requests from SAP system.

        Fetches transport requests from the SAP Transport Organizer based on the user's
        saved configuration in Eclipse ADT. The results are filtered according to the
        settings stored in that configuration (user, status, transport type, etc.).

        Args:
            targets: Include target system information (default: True)
            transport_number: Optional transport number to filter by (e.g., 'D2AK904114').
                            Can include wildcards (*) for pattern matching.

        Returns:
            ListTransportsResult with list of transport requests and total count

        Examples:
            # List transports using your default configuration
            >>> result = client.list_transports()
            >>> for tr in result['TRANSPORTS']:
            ...     print(f"{tr['TRKORR']}: {tr['DESCRIPTION']}")
            ...     print(f"  Type: {tr['TYPE']} | Status: {tr['STATUS']} | Owner: {tr['OWNER']}")
            
            # Search for specific transport (including released ones)
            >>> result = client.list_transports(transport_number='D2AK904114')
            
            # Search with pattern
            >>> result = client.list_transports(transport_number='D2AK9041*')

        Note:
            The filters (user, status, transport type) come from your saved configuration
            in Eclipse ADT's Transport Organizer. To change filters:
            1. Open Eclipse ADT
            2. Go to Transport Organizer view
            3. Adjust filters and save the configuration

            This is useful for:
            - Listing available transports before locking an object
            - Finding existing transports to reuse
            - Auditing open transports
            - Checking status of released transports (use transport_number filter)
        """
        http_request_parameters = self.build_request_parameters()
        response = list_transports(http_request_parameters, targets, transport_number)
        return response

    def get_transport_objects(self, transport_number: str) -> List[Dict[str, Any]]:
        """Get list of objects in a transport request.
        
        Args:
            transport_number: Transport request number (e.g., "DHAK905111")
            
        Returns:
            List of objects with PGMID, TYPE, NAME, OBJ_DESC, POSITION, etc.
            
        Example:
            >>> objects = client.get_transport_objects("DHAK905111")
            >>> for obj in objects:
            ...     print(f"{obj['TYPE']}: {obj['NAME']}")
        """
        from .api.listtransports import get_transport_objects
        http_request_parameters = self.build_request_parameters()
        objects = get_transport_objects(http_request_parameters, transport_number)
        return [dict(obj) for obj in objects]  # Convert TypedDict to regular dict

    def get_searchable_object_types(self) -> Dict[str, Dict[str, str]]:
        """Get list of all SAP object types available in the system for searching.

        This includes both creatable and non-creatable object types.

        Returns:
            Dictionary with object types and their descriptions, e.g.:
            {
                "CLAS/OC": {"type": "CLAS/OC", "description": "Class"},
                "PROG/P": {"type": "PROG/P", "description": "Program"},
                "SRVD/SRV": {"type": "SRVD/SRV", "description": "Service Definition"},
                "SRVB/SVB": {"type": "SRVB/SVB", "description": "Service Binding"},
                ...
            }

        Examples:
            >>> types = client.get_searchable_object_types()
            >>> # Search for only service definitions
            >>> client.search_object("Z*", max_results=10, object_type=types["SRVD/SRV"]["type"])
        """
        http_request_parameters = self.build_request_parameters()
        response = get_searchable_object_types(http_request_parameters)
        return response

    def get_odata_metadata(
        self,
        service_name: str,
        service_namespace: Optional[str] = None,
        odata_version: Literal["v2", "v4"] = "v4",
    ) -> str:
        """
        Fetch raw metadata XML from an OData service (V2 or V4).

        Uses the existing ADT client session and credentials to fetch OData metadata,
        ensuring consistent authentication and session management across all SAP operations.

        Args:
            service_name: OData service name
            service_namespace: Service namespace (optional for v2, required for v4)
            odata_version: OData version ("v2" or "v4")
            client_override: Optional client number to override the default client

        Returns:
            Raw metadata XML as string

        Raises:
            Exception: If metadata fetch fails

        Examples:
            >>> # Get OData v4 metadata
            >>> metadata = client.get_odata_metadata(
            ...     service_name="ZMY_SERVICE",
            ...     service_namespace="ZMY_SERVICE_NS",
            ...     odata_version="v4"
            ... )
            >>>
            >>> # Get OData v2 metadata
            >>> metadata_v2 = client.get_odata_metadata(
            ...     service_name="ZAPI_SERVICE_SRV",
            ...     odata_version="v2"
            ... )
        """
        http_request_parameters = self.build_request_parameters()
        response = get_odata_metadata(
            http_request_parameters, service_name, service_namespace, odata_version
        )
        return response

    def call_odata_service(
        self,
        http_method: str,
        service_name: str,
        entity_name: str,
        service_namespace: Optional[str] = None,
        odata_version: Literal["v2", "v4"] = "v4",
        query_parameters: Optional[dict] = None,
        request_body: Optional[dict] = None,
    ) -> Dict[str, Any]:
        """
        Call an OData service with any HTTP method.

        Uses the existing ADT client session and credentials to make OData API calls,
        ensuring consistent authentication and session management across all SAP operations.
        Automatically handles CSRF tokens for state-changing operations.

        Args:
            http_method: HTTP method (GET, POST, PUT, PATCH, DELETE)
            service_name: OData service name
            entity_name: Entity name or path (e.g., "Products", "Products('123')")
            service_namespace: Service namespace (optional for v2, required for v4)
            odata_version: OData version ("v2" or "v4")
            query_parameters: Query parameters dict (e.g., {"$filter": "Price gt 100"})
            request_body: Request body for POST/PUT/PATCH operations

        Returns:
            Dictionary containing API response data

        Raises:
            Exception: If API call fails

        Examples:
            >>> # GET request
            >>> data = client.call_odata_service(
            ...     http_method="GET",
            ...     service_name="ZMY_SERVICE",
            ...     entity_name="Products",
            ...     service_namespace="ZMY_SERVICE_NS",
            ...     odata_version="v4",
            ...     query_parameters={"$filter": "Price gt 100", "$top": 10}
            ... )
            >>>
            >>> # POST request (create)
            >>> result = client.call_odata_service(
            ...     http_method="POST",
            ...     service_name="ZMY_SERVICE",
            ...     entity_name="Products",
            ...     service_namespace="ZMY_SERVICE_NS",
            ...     odata_version="v4",
            ...     request_body={"Name": "New Product", "Price": 150}
            ... )
        """
        http_request_parameters = self.build_request_parameters()

        response = call_odata_service(
            http_request_parameters,
            http_method,
            service_name,
            entity_name,
            service_namespace,
            odata_version,
            query_parameters,
            request_body,
        )
        return response

    def get_ddic_object_metadata(
        self,
        object_name: str,
        object_type: DDIC_OBJECT_TYPES = "cds",
    ) -> str:
        """
        Fetch metadata for data preview-enabled objects (CDS Views and Transparent Tables).

        This method uses the ADT data preview endpoint which is specifically designed for
        objects where you can preview data in Eclipse ADT.

        **Supported Object Types:**
        - CDS Views (object_type="cds")
        - Transparent Tables (object_type="ddic")

        **Not Supported:**
        - DDIC Structures
        - Table Types
        - Data Elements
        - Domains
        - Database Views

        The metadata includes comprehensive column information such as:
        - Column names and camelCase names
        - Data types and lengths
        - Descriptions
        - Key attributes
        - Whether columns are key figures

        Args:
            object_name: Name of the CDS view or transparent table (e.g., "ZI_HEADCUST", "MARA")
            object_type: Type of object - "cds" for CDS Views or "ddic" for transparent tables (default: "ddic")

        Returns:
            Raw metadata XML response as string containing column definitions,
            data types, key attributes, and structural information

        Raises:
            Exception: If metadata fetch fails or object doesn't support data preview

        Examples:
            >>> # Connect to SAP first
            >>> import base64
            >>> token = base64.b64encode(b"user:pass").decode('ascii')
            >>> client = AdtClient("https://sap.example.com", "110", token)
            >>> client.login()
            >>>
            >>> # Get CDS View metadata
            >>> metadata = client.get_ddic_object_metadata("ZI_HEADCUST", "cds")
            >>>
            >>> # Get transparent table metadata
            >>> metadata = client.get_ddic_object_metadata("MARA", "ddic")
        """
        http_request_parameters = self.build_request_parameters()
        response = get_ddic_metadata(
            http_request_parameters,
            object_name,
            object_type,
        )
        return response

    def preview_ddic_data(
        self,
        object_name: str,
        sql_query: str,
        row_number: int = 100,
    ) -> str:
        """
        Execute a SQL query and retrieve data preview for a DDIC object.

        This method uses the ADT data preview endpoint to execute SQL queries
        against database tables or CDS views and retrieve the result set.

        **Supported Object Types:**
        - Database Tables (transparent tables)
        - CDS Views (Core Data Services)

        **Use Cases:**
        - Previewing table/view data
        - Executing custom SQL queries
        - Testing data retrieval
        - Analyzing data structure

        Args:
            object_name: Name of the table or CDS view to query (e.g., "MARA", "ZI_HEADCUST")
            sql_query: SQL SELECT statement to execute
            row_number: Maximum number of rows to return (default: 100)

        Returns:
            Raw XML response containing:
            - Column metadata (names, types, descriptions, key attributes)
            - Data rows organized by column
            - Total row count and query execution time

        Raises:
            Exception: If data preview fails

        Examples:
            >>> # Connect to SAP first
            >>> import base64
            >>> token = base64.b64encode(b"user:pass").decode('ascii')
            >>> client = AdtClient("https://sap.example.com", "110", token)
            >>> client.login()
            >>>
            >>> # Preview all data from a table
            >>> sql = "SELECT * FROM ZDT_SD_RULE"
            >>> data = client.preview_ddic_data("ZDT_SD_RULE", sql, row_number=50)
            >>>
            >>> # Preview with WHERE clause
            >>> sql = "SELECT MATNR, MAKTX FROM MARA WHERE MTART = 'ZMAT'"
            >>> data = client.preview_ddic_data("MARA", sql, row_number=100)
        """
        http_request_parameters = self.build_request_parameters()
        response = preview_ddic_data(
            http_request_parameters,
            object_name,
            sql_query,
            row_number,
        )
        return response

    # Debugger API Methods
    def debugger_listeners(
        self,
        debugging_mode: DebuggingMode,
        terminal_id: str,
        ide_id: str,
        request_user: Optional[str] = None,
        check_conflict: bool = True
    ) -> Optional[Union[Debuggee, DebugListenerError]]:
        """Check for active debugging sessions and manage debuggee connections.
        
        Query the SAP system for active debug sessions that match the specified
        terminal and IDE identifiers. Used to discover programs waiting to be debugged.
        
        Args:
            debugging_mode: "user" or "terminal" debugging mode
            terminal_id: Terminal identifier (unique per terminal session)
            ide_id: IDE identifier (unique per IDE instance)
            request_user: Optional SAP username filter
            check_conflict: Check for conflicting debug sessions
            
        Returns:
            Debuggee object if found, DebugListenerError if error, or None if no debuggees
        """
        http_request_parameters = self.build_request_parameters()
        return debugger_listeners(
            http_request_parameters,
            debugging_mode,
            terminal_id,
            ide_id,
            request_user,
            check_conflict
        )

    def debugger_attach(
        self,
        debugging_mode: DebuggingMode,
        debuggee_id: str,
        request_user: str = "",
        dynpro_debugging: bool = True
    ) -> DebugAttach:
        """Attach to a running ABAP program for debugging.
        
        After discovering a debuggee, attach the debugger to establish a debugging
        session where you can set breakpoints, inspect variables, and step through code.
        
        Args:
            debugging_mode: "user" or "terminal" debugging mode
            debuggee_id: ID of the debuggee to attach to (from debugger_listeners)
            request_user: SAP username requesting the debug session
            dynpro_debugging: Enable dynpro (screen) debugging
            
        Returns:
            DebugAttach object with attachment status and available actions
        """
        http_request_parameters = self.build_request_parameters()
        return debugger_attach(
            http_request_parameters,
            debugging_mode,
            debuggee_id,
            request_user,
            dynpro_debugging
        )

    def debugger_set_breakpoints(
        self,
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
        """
        http_request_parameters = self.build_request_parameters()
        return debugger_set_breakpoints(
            http_request_parameters,
            debugging_mode,
            terminal_id,
            ide_id,
            client_id,
            breakpoints,
            request_user,
            scope,
            system_debugging,
            deactivated
        )

    def debugger_delete_breakpoint(
        self,
        breakpoint_id: str,
        debugging_mode: DebuggingMode,
        terminal_id: str,
        ide_id: str,
        request_user: Optional[str] = None,
        scope: DebuggerScope = "external"
    ) -> bool:
        """Delete a specific breakpoint.
        
        Args:
            breakpoint_id: ID of the breakpoint to delete
            debugging_mode: "user" or "terminal" debugging mode
            terminal_id: Terminal identifier
            ide_id: IDE identifier
            request_user: SAP username
            scope: "external" or "debugger" scope
            
        Returns:
            True if successful
        """
        http_request_parameters = self.build_request_parameters()
        return debugger_delete_breakpoint(
            http_request_parameters,
            breakpoint_id,
            debugging_mode,
            terminal_id,
            ide_id,
            request_user,
            scope
        )

    def debugger_step(
        self,
        method: DebugStepType,
        uri: Optional[str] = None
    ) -> DebugStep:
        """Execute a step operation in the debugger.
        
        Control the execution flow of the debugged program.
        
        Args:
            method: Step type - "stepInto", "stepOver", "stepReturn", "stepContinue", etc.
            uri: Optional URI for stepRunToLine or stepJumpToLine
            
        Returns:
            DebugStep object with execution status
        """
        http_request_parameters = self.build_request_parameters()
        return debugger_step(http_request_parameters, method, uri)

    def debugger_stack(self, semantic_uris: bool = True) -> Dict[str, Any]:
        """Get the current call stack.
        
        Retrieve the call stack showing the sequence of program calls.
        
        Args:
            semantic_uris: Use semantic URIs for stack entries
            
        Returns:
            Dictionary with call stack information
        """
        http_request_parameters = self.build_request_parameters()
        return debugger_stack(http_request_parameters, semantic_uris)

    def debugger_variables(self, variable_ids: List[str]) -> List[DebugVariable]:
        """Get variable values by their IDs.
        
        Retrieve detailed information about specific variables including their
        values, types, and metadata.
        
        Args:
            variable_ids: List of variable IDs to retrieve
            
        Returns:
            List of DebugVariable objects with variable details
        """
        http_request_parameters = self.build_request_parameters()
        return debugger_variables(http_request_parameters, variable_ids)

    def debugger_child_variables(
        self,
        parent_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Get child variables for complex types (structures, tables, objects).
        
        For variables of complex types, retrieve their child/nested variables.
        
        Args:
            parent_ids: List of parent variable IDs (default: ["@ROOT", "@DATAAGING"])
            
        Returns:
            Dictionary with hierarchies and child variables
        """
        http_request_parameters = self.build_request_parameters()
        return debugger_child_variables(http_request_parameters, parent_ids)

    def debugger_set_variable_value(
        self,
        variable_name: str,
        value: str
    ) -> str:
        """Set the value of a variable during debugging.
        
        Modify a variable's value at runtime.
        
        Args:
            variable_name: Name of the variable to modify
            value: New value to set
            
        Returns:
            Response body from the operation
        """
        http_request_parameters = self.build_request_parameters()
        return debugger_set_variable_value(
            http_request_parameters,
            variable_name,
            value
        )

    def debugger_save_settings(self, settings: DebugSettings) -> DebugSettings:
        """Save debugger settings.
        
        Configure global debugger behavior such as when to break.
        
        Args:
            settings: Debugger settings to apply
            
        Returns:
            Updated debugger settings
        """
        http_request_parameters = self.build_request_parameters()
        return debugger_save_settings(http_request_parameters, settings)

    def debugger_go_to_stack(self, stack_uri: str) -> bool:
        """Navigate to a specific stack level.
        
        Jump to a different level in the call stack to inspect that context.
        
        Args:
            stack_uri: URI of the stack level
            
        Returns:
            True if successful
        """
        http_request_parameters = self.build_request_parameters()
        return debugger_go_to_stack(http_request_parameters, stack_uri)

    # Service Binding Operations
    
    def create_service_binding(
        self,
        name: str,
        package: str,
        description: str,
        service_definition: str,
        service_binding_version: ServiceBindingVersion = "ODATA\\CV4",
        corr_nr: str | None = None,
    ) -> dict:
        """Create a new Service Binding.
        
        Service Bindings expose Service Definitions as consumable services (OData, SQL, INA).
        
        Args:
            name: Service binding name (e.g., "Z_MY_SERVICE_BIND")
            package: Package name (e.g., "$TMP" or "ZPACKAGE")
            description: Description of the service binding
            service_definition: Name of the service definition to bind (must exist)
            service_binding_version: Binding type/version
                - "ODATA\\CV4": OData V4 (modern RAP)
                - "ODATA\\CV2": OData V2 (legacy Gateway)
                - "SQL": SQL Service
                - "INA": InA Service (Analytics)
            corr_nr: Transport request number (required for custom packages, optional for $TMP)
        
        Returns:
            Dictionary with uri, etag, status_code, and response_body
            
        Example:
            >>> result = client.create_service_binding(
            ...     name="Z_CUSTOMER_API",
            ...     package="ZPACKAGE",
            ...     description="Customer API",
            ...     service_definition="Z_CUSTOMER_DEF",
            ...     service_binding_version="ODATA\\CV4"
            ... )
            >>> print(result["uri"])
        """
        http_request_parameters = self.build_request_parameters()
        return create_service_binding(
            http_request_parameters,
            name,
            package,
            description,
            service_definition,
            self.username,
            service_binding_version,
            corr_nr,
        )
    
    def publish_service_binding(
        self,
        name: str,
        binding_type: Literal["odatav4", "odatav2", "sql", "ina"] = "odatav4",
    ) -> ServiceBindingPublishStatus:
        """Publish a Service Binding to make it accessible.
        
        Publishing activates the service binding and makes it available for consumption.
        
        Args:
            name: Service binding name
            binding_type: Type of binding ("odatav4", "odatav2", "sql", "ina")
        
        Returns:
            ServiceBindingPublishStatus with severity, short_text, long_text
            
        Example:
            >>> status = client.publish_service_binding(
            ...     name="Z_CUSTOMER_API",
            ...     binding_type="odatav4"
            ... )
            >>> print(status["short_text"])  # "Z_CUSTOMER_API published locally"
        """
        http_request_parameters = self.build_request_parameters()
        return publish_service_binding(
            http_request_parameters,
            name,
            binding_type,
        )
    
    def unpublish_service_binding(
        self,
        name: str,
        binding_type: Literal["odatav4", "odatav2", "sql", "ina"] = "odatav4",
    ) -> ServiceBindingPublishStatus:
        """Unpublish a Service Binding to deactivate it.
        
        Unpublishing removes the service endpoint.
        
        Args:
            name: Service binding name
            binding_type: Type of binding ("odatav4", "odatav2", "sql", "ina")
        
        Returns:
            ServiceBindingPublishStatus with severity, short_text, long_text
            
        Example:
            >>> status = client.unpublish_service_binding(
            ...     name="Z_CUSTOMER_API",
            ...     binding_type="odatav4"
            ... )
        """
        http_request_parameters = self.build_request_parameters()
        return unpublish_service_binding(
            http_request_parameters,
            name,
            binding_type,
        )
    
    def get_binding_types(self) -> list:
        """Get available service binding types from the SAP system.
        
        Returns:
            List of dictionaries with name, description, data keys
            
        Example:
            >>> types = client.get_binding_types()
            >>> for t in types:
            ...     print(f"{t['name']}: {t['data']}")
        """
        http_request_parameters = self.build_request_parameters()
        return get_binding_types(http_request_parameters)
