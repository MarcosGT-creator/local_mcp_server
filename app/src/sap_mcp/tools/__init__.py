"""
MCP Tools - Auto-discovered by FileSystemProvider

Each Python file in this directory contains tools that are automatically
registered when the server starts. Use the standalone @tool decorator.

Tool Categories:
- connection.py: SAP connection management
- search.py: Object search and discovery
- source.py: Source code operations (get/set, lock/unlock, syntax check)
- activation.py: Object activation and inactive object management
- transport.py: Transport request management
- odata.py: OData service calls and metadata
- ddic.py: DDIC object metadata and data preview
- objects.py: Object manipulation (delete, change package, tests)
- service_binding.py: Service binding creation and publishing
"""

# Import all tools to make them available for FileSystemProvider discovery
from .connection import connect_to_sap
from .search import search_object, get_package_objects
from .source import (
    lock_object,
    unlock_object,
    get_object_source,
    set_object_source,
    get_object_structure,
    syntax_check,
    format_source_code,
)
from .activation import activate_object, get_inactive_objects, activate_multiple_objects
from .transport import (
    transport_check,
    create_transport_and_assign,
    create_transport_organizer,
    list_transports,
    get_transport_objects,
)
from .odata import get_metadata, call_sap_api_generic
from .ddic import get_ddic_object_metadata, preview_ddic_data
from .objects import (
    delete_object,
    change_package,
    create_test_class_include,
    run_unit_test,
    create_object,
    get_creatable_object_types,
)
from .service_binding import (
    create_and_publish_service_binding,
    get_service_binding_types,
)

__all__ = [
    # Connection
    "connect_to_sap",
    # Search
    "search_object",
    "get_package_objects",
    # Source
    "lock_object",
    "unlock_object",
    "get_object_source",
    "set_object_source",
    "get_object_structure",
    "syntax_check",
    "format_source_code",
    # Activation
    "activate_object",
    "get_inactive_objects",
    "activate_multiple_objects",
    # Transport
    "transport_check",
    "create_transport_and_assign",
    "create_transport_organizer",
    "list_transports",
    "get_transport_objects",
    # OData
    "get_metadata",
    "call_sap_api_generic",
    # DDIC
    "get_ddic_object_metadata",
    "preview_ddic_data",
    # Objects
    "delete_object",
    "change_package",
    "create_test_class_include",
    "run_unit_test",
    "create_object",
    "get_creatable_object_types",
    # Service Binding
    "create_and_publish_service_binding",
    "get_service_binding_types",
]
