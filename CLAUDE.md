# CLAUDE.md - SAP MCP Server

## Project Overview
Help Reference: https://github.com/vaibhavgoel-github-1986/sap-mcp-server-docs
MCP (Model Context Protocol) server that bridges AI agents with SAP systems via the ADT (ABAP Development Tools) REST API. It exposes SAP/ABAP development operations as MCP tools, enabling AI agents to programmatically create, modify, search, debug, and manage ABAP objects in a live SAP system.

## Architecture

```
app/
├── start_server.py                  # Entry point
├── requirements.txt                 # Python dependencies
└── src/
    ├── server.py                    # FastMCP server setup, middleware, routes
    ├── abap_adt_client/             # Low-level SAP ADT HTTP client
    │   ├── adt_client.py            # AdtClient class (~40 SAP operations)
    │   ├── http_request.py          # HTTP request parameter types
    │   ├── response_parsing.py      # XML response parsing utilities
    │   └── api/                     # Individual ADT API implementations
    │       ├── login.py             # Authentication & CSRF token fetch
    │       ├── search.py            # Object search
    │       ├── content.py           # Source code get/set
    │       ├── lock.py              # Object lock/unlock (stateful sessions)
    │       ├── create.py            # Object creation (classes, programs, CDS, etc.)
    │       ├── delete.py            # Object deletion
    │       ├── activate.py          # Object activation (single & batch)
    │       ├── syntax.py            # Syntax check
    │       ├── prettyprint.py       # ABAP pretty printer
    │       ├── unittest.py          # ABAP Unit test execution
    │       ├── objectstructure.py   # Object structure/metadata
    │       ├── objecttypes.py       # Searchable object types
    │       ├── virtualfolders.py    # Package contents browsing
    │       ├── transportcheck.py    # Transport check for objects
    │       ├── createtransport.py   # Transport request creation
    │       ├── listtransports.py    # Transport listing & objects
    │       ├── changepackage.py     # Package reassignment
    │       ├── odata.py             # OData service calls & metadata (v2/v4)
    │       ├── datapreview.py       # DDIC data preview (SQL on tables/CDS)
    │       ├── ddic_types.py        # DDIC type definitions
    │       ├── debugger.py          # Full remote debugger API
    │       ├── service_binding.py   # Service binding CRUD & publish
    │       └── xml_namespaces.py    # SAP XML namespace constants
    ├── sap_mcp/                     # MCP tool layer
    │   └── tools/                   # Auto-discovered by FileSystemProvider
    │       ├── __init__.py          # Tool registry & exports
    │       ├── _helpers.py          # Shared helpers (get_adt_client_safe)
    │       ├── connection.py        # connect_to_sap
    │       ├── search.py            # search_object, get_package_objects
    │       ├── source.py            # lock/unlock, get/set source, syntax check, format
    │       ├── activation.py        # activate_object, get_inactive_objects, activate_multiple
    │       ├── transport.py         # transport_check, create/list transports
    │       ├── objects.py           # create/delete object, change package, unit test
    │       ├── odata.py             # get_metadata, call_sap_api_generic
    │       ├── ddic.py              # get_ddic_object_metadata, preview_ddic_data
    │       ├── service_binding.py   # create_and_publish_service_binding
    │       └── tasks.py             # Task-related tools
    └── utils/                       # Shared utilities
        ├── adt_pool.py              # Thread-safe ADT connection pool
        ├── constants.py             # Server config, defaults, error messages
        ├── context.py               # ContextVar for async-safe client access
        ├── credentials.py           # SAPCredentials dataclass (from headers)
        ├── logger.py                # Structured logging
        └── registration.py          # Tool registration utilities
```

## Tech Stack

| Component           | Technology                              |
|---------------------|-----------------------------------------|
| MCP Framework       | `fastmcp 3.0.0b1` (streamable-http)    |
| Web Server          | `uvicorn 0.40.0` + `FastAPI 0.128.0`   |
| HTTP Client (SAP)   | `requests 2.32.5` + `httpx 0.28.1`     |
| Data Validation     | `pydantic 2.12.5`                       |
| Config              | `python-dotenv 1.2.1`                   |
| SAP OData           | `sap-odata-python 1.2.0`               |
| Python              | 3.x (uses type hints, ContextVar, dataclasses) |

## Server Configuration

- **Host:** `0.0.0.0`
- **Port:** `8001`
- **MCP Path:** `/mcp/`
- **Transport:** `streamable-http`
- **Health Check:** `GET /health`
- **Pool Stats:** `GET /pool-stats`

## Authentication Model

Credentials are passed per-request via HTTP headers:

| Header         | Description                  | Required |
|----------------|------------------------------|----------|
| `x-hostname`   | SAP system URL               | Yes      |
| `x-username`   | SAP username                 | Yes      |
| `x-password`   | SAP password                 | Yes      |
| `x-client`     | SAP client number            | No (default: `110`) |

The `SAPMiddleware` extracts these headers on every `call_tool` request, uses the connection pool (`AdtClientPool`) to get or create an `AdtClient`, and stores it in a `ContextVar` for async-safe access by tools.

Alternatively, the `connect_to_sap` tool can be called explicitly by the AI agent.

## Connection Pool

- **Implementation:** `AdtClientPool` in `utils/adt_pool.py`
- **Thread-safe:** Uses `threading.Lock`
- **Key:** SHA-256 hash of `hostname:client:username`
- **Max connections:** 50 (configurable)
- **Max idle time:** 30 minutes (1800s)
- **Auto-cleanup:** Stale connections removed on each `get_or_create` call
- **Eviction:** LRU when at capacity

## MCP Tools Exposed

### Connection
- `connect_to_sap` - Initialize SAP connection (optional if using headers)

### Search & Discovery
- `search_object` - Search for ABAP objects by name/pattern
- `get_package_objects` - List objects in a package (virtual folders API)

### Source Code Operations
- `get_object_source` - Read source code (active/inactive/workingArea versions)
- `set_object_source` - Write source code (requires lock + transport)
- `lock_object` - Lock object for editing (switches to stateful session)
- `unlock_object` - Release lock
- `get_object_structure` - Get object metadata/structure
- `syntax_check` - Check ABAP syntax
- `format_source_code` - Pretty print ABAP source

### Object Lifecycle
- `create_object` - Create new ABAP objects (class, program, CDS, function group, etc.)
- `delete_object` - Delete an object (requires lock)
- `change_package` - Move object between packages
- `create_test_class_include` - Create test class include for a class
- `run_unit_test` - Execute ABAP Unit tests
- `get_creatable_object_types` - List available object types for creation

### Activation
- `activate_object` - Activate a single object
- `get_inactive_objects` - List inactive objects for current user
- `activate_multiple_objects` - Batch activation via background job API

### Transport Management
- `transport_check` - Check transport requirements for an object
- `create_transport_and_assign` - Create transport tied to an object
- `create_transport_organizer` - Create standalone transport request
- `list_transports` - List transport requests (with optional filters)
- `get_transport_objects` - List objects in a transport

### OData Services
- `get_metadata` - Fetch OData service metadata XML (v2/v4)
- `call_sap_api_generic` - Execute OData calls (GET/POST/PUT/PATCH/DELETE)

### Data Dictionary (DDIC)
- `get_ddic_object_metadata` - Get metadata for CDS views and transparent tables
- `preview_ddic_data` - Execute SQL queries against tables/CDS views

### Service Bindings
- `create_and_publish_service_binding` - Create and publish OData/SQL/INA service bindings
- `get_service_binding_types` - List available binding types

## Key Design Patterns

1. **Two-layer architecture:** Low-level `AdtClient` (pure HTTP/XML) is decoupled from MCP tool definitions. Tools are thin wrappers.
2. **Auto-discovery:** Tools are auto-registered via `FileSystemProvider` scanning the `sap_mcp/tools/` directory for `@tool` decorated functions.
3. **Middleware pipeline:** `SAPMiddleware` handles auth per-request; `DetailedTimingMiddleware` for performance monitoring.
4. **ContextVar for client access:** `get_adt_client()` / `set_adt_client()` use Python `contextvars` for async-safe per-request client storage.
5. **Stateful sessions:** Lock/unlock operations switch the ADT client to stateful mode (SAP requires server affinity for locks).
6. **CSRF token management:** Login fetches the CSRF token; subsequent requests include it for state-changing operations.

## Common Development Tasks

### Start the server
```bash
cd app
python start_server.py
```

### Add a new MCP tool
1. Create or edit a file in `app/src/sap_mcp/tools/`
2. Decorate the function with `@tool` from `fastmcp`
3. Use `get_adt_client_safe()` from `_helpers.py` to get the ADT client
4. Export it in `app/src/sap_mcp/tools/__init__.py`
5. The `FileSystemProvider` will auto-discover it on next restart

### Add a new ADT API operation
1. Create a module in `app/src/abap_adt_client/api/`
2. Accept `HttpRequestParameters` as first argument
3. Add a wrapper method in `AdtClient` class (`adt_client.py`)
4. Import in `app/src/abap_adt_client/api/__init__.py`

## Important Notes

- SAP ADT uses XML-based request/response bodies (not JSON)
- Lock operations require stateful sessions; remember to unlock after editing
- Object activation is separate from saving source code
- Transport requests are required for objects in custom packages (not `$TMP`)
- The debugger API requires terminal/IDE identifiers for session management
- SAP usernames are always uppercase internally
