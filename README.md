# SAP MCP Server

Servidor [MCP](https://modelcontextprotocol.io) que conecta agentes de IA con sistemas SAP
a traves de la API REST de **ADT** (ABAP Development Tools).

Expone las operaciones de desarrollo ABAP como herramientas MCP, de forma que un agente
(Claude Code, Claude Desktop, etc.) puede buscar, leer, crear, modificar, activar y depurar
objetos ABAP en un sistema SAP real, ademas de gestionar ordenes de transporte, ejecutar
ABAP Unit y consultar datos del diccionario.

---

## Requisitos

- Docker y Docker Compose
- Un sistema SAP con los servicios ADT (`/sap/bc/adt/*`) activados en SICF
- Un usuario SAP con permisos de desarrollo

## Inicio rapido

```powershell
# Windows / PowerShell
./start.ps1 -Hostname "https://vhmtjds4ci.fra3.sap.torres.es:20400/" -Username "tu_usuario" -Password "tu_password"
```

```bash
# Linux / macOS / Git Bash
SAP_HOSTNAME="https://vhmtjds4ci.fra3.sap.torres.es:20400/" \
SAP_USERNAME="tu_usuario" SAP_PASSWORD="tu_password" SAP_CLIENT="100" \
docker compose up -d
```

Comprobar que responde:

```bash
curl http://localhost:8001/health
```

El `.mcp.json` del repo ya apunta a `http://localhost:8001/mcp/`, asi que al abrir Claude Code
desde este directorio el servidor se detecta solo. Verificalo con `/mcp`.

> Para levantar **dos entornos a la vez** (desarrollo y calidad, puertos 8001 y 8002), usar
> `./start_dev_qas.ps1`. Los detalles estan en [SETUP.md](SETUP.md).

## Configuracion

Las credenciales SAP **no se versionan**. Hay tres formas de suministrarlas:

| Metodo | Cuando usarlo |
|---|---|
| Cabeceras HTTP (`x-hostname`, `x-username`, `x-password`, `x-client`) | El cliente MCP gestiona las credenciales por peticion. **Tienen prioridad** sobre las variables de entorno |
| Variables de entorno del contenedor (`SAP_HOSTNAME`, `SAP_USERNAME`, `SAP_PASSWORD`, `SAP_CLIENT`) | Lo habitual: se pasan al arrancar con `start.ps1` o `docker compose up`. Se usan como fallback si no llegan cabeceras |
| Tool `connect_to_sap` | Alternativa: el agente conecta de forma interactiva, sin nada preconfigurado |

Si prefieres no teclearlas en cada arranque, copia la plantilla y rellenala:

```bash
cp .env.example .env
```

`.env` esta en `.gitignore`: nunca se sube al repositorio.

## Endpoints

| Ruta | Descripcion |
|---|---|
| `POST /mcp/` | Endpoint MCP (transporte `streamable-http`) |
| `GET /health` | Health check |
| `GET /pool-stats` | Estado del pool de conexiones ADT |

## Herramientas MCP

30 tools agrupadas por area:

| Area | Tools |
|---|---|
| **Conexion** | `connect_to_sap` |
| **Busqueda** | `search_object`, `get_package_objects` |
| **Codigo fuente** | `get_object_source`, `set_object_source`, `lock_object`, `unlock_object`, `get_object_structure`, `syntax_check`, `format_source_code` |
| **Ciclo de vida** | `create_object`, `delete_object`, `change_package`, `create_test_class_include`, `run_unit_test`, `get_creatable_object_types` |
| **Activacion** | `activate_object`, `get_inactive_objects`, `activate_multiple_objects` |
| **Transportes** | `transport_check`, `create_transport_and_assign`, `create_transport_organizer`, `list_transports`, `get_transport_objects` |
| **OData** | `get_metadata`, `call_sap_api_generic` |
| **Diccionario (DDIC)** | `get_ddic_object_metadata`, `preview_ddic_data` |
| **Service bindings** | `create_and_publish_service_binding`, `get_service_binding_types` |

Flujo tipico de modificacion: `lock_object` → `set_object_source` → `syntax_check` →
`activate_object` → `unlock_object`. Los objetos fuera de `$TMP` requieren una orden de
transporte.

## Arquitectura

```
Cliente MCP (Claude Code / Desktop)
    │  HTTP :8001  (credenciales por cabecera o env del contenedor)
    ▼
Contenedor Docker - FastMCP + uvicorn
    │  HTTPS  (Basic Auth + token CSRF, sesiones stateful para locks)
    ▼
Sistema SAP - ADT REST API
```

Dos capas bien separadas:

- **`abap_adt_client/`** — cliente HTTP de bajo nivel contra ADT. Habla XML, gestiona login,
  token CSRF, locks y sesiones stateful. No sabe nada de MCP.
- **`sap_mcp/tools/`** — capa MCP. Envoltorios finos sobre el cliente, descubiertos
  automaticamente por el `FileSystemProvider` de FastMCP.

```
app/
├── start_server.py          # Entry point
├── requirements.txt
└── src/
    ├── server.py            # FastMCP, middlewares, rutas
    ├── abap_adt_client/     # Cliente ADT (adt_client.py + api/)
    ├── sap_mcp/tools/       # Tools MCP (auto-descubiertas)
    └── utils/               # Pool de conexiones, contexto, logging, constantes
```

El `SAPMiddleware` extrae las credenciales de cada peticion, obtiene un cliente del
`AdtClientPool` (thread-safe, max. 50 conexiones, 30 min de inactividad) y lo deja en un
`ContextVar` para que las tools accedan a el de forma segura en async.

## Stack

Python 3.12 · `fastmcp 3.0.0b1` · `uvicorn` + `FastAPI` · `requests` / `httpx` · `pydantic`

## Documentacion

| Fichero | Contenido |
|---|---|
| [SETUP.md](SETUP.md) | Instalacion paso a paso, modo dev+qas, configuracion de clientes MCP, troubleshooting |
| [CLAUDE.md](CLAUDE.md) | Guia para agentes de IA que trabajen sobre este codigo: estructura, patrones y como anadir tools o APIs |

## Notas

- ADT usa XML en peticiones y respuestas, no JSON.
- Los locks exigen sesion stateful; acuerdate de hacer `unlock_object` al terminar.
- Guardar el codigo fuente y activarlo son dos operaciones distintas.
- Si SAP responde `403 "Service cannot be reached"`, el nodo `/sap/bc/adt/` no esta activado
  en SICF.
