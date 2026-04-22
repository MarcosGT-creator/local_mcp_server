# SAP MCP Server - Setup Guide

## Prerequisites

- Docker y Docker Compose instalados
- Acceso a un sistema SAP con ADT habilitado

## Estructura del proyecto

```
local_mcp_server/
├── app/                        # Codigo fuente del servidor
│   ├── start_server.py         # Entry point
│   ├── requirements.txt        # Dependencias Python
│   └── src/                    # Modulos del servidor
├── Dockerfile                  # Imagen del servidor MCP
├── docker-compose.yml          # Orquestacion del contenedor
├── start.ps1                   # Script de arranque (PowerShell)
├── .env                        # Variables de entorno (opcional, fallback)
├── .env.example                # Plantilla de variables de entorno
└── .dockerignore               # Exclusiones del build context
```

## Paso 1: Construir la imagen (solo la primera vez o tras cambios)

```bash
docker compose build
```

## Paso 2: Levantar el servidor

Las credenciales SAP se pasan directamente al arrancar el contenedor.
Hosts:
MTD: https://bfwin07.torres.es:1443/
MTI:
MTP:
DS4: https://vhmtjds4ci.fra3.sap.torres.es:20400/
QS4: https://vhmtjqs4ci.fra3.sap.torres.es:20400/

### PowerShell (recomendado en Windows) 

```powershell
./start.ps1 -Hostname "https://vhmtjds4ci.fra3.sap.torres.es:20400/" -Username "mgarcia" -Password "tu_password"
```

Con client diferente al default (100):

```powershell
./start.ps1 -Hostname "https://vhmtjds4ci.fra3.sap.torres.es:20400/" -Username "mgarcia" -Password "tu_password" -Client "200"
```

### Linux / macOS / Git Bash

```bash
SAP_HOSTNAME="https://vhmtjds4ci.fra3.sap.torres.es:20400/" SAP_USERNAME="mgarcia" SAP_PASSWORD="tu_password" SAP_CLIENT="100" docker compose up -d
```

### Alternativa: usar fichero .env

Si prefieres no pasar las credenciales cada vez, puedes crear un fichero `.env` con los valores:

```bash
cp .env.example .env
# Editar .env con tus credenciales SAP
```

Y luego simplemente:

```bash
docker compose up -d
```

Esto arranca:

| Servicio       | Contenedor   | Puerto  | Descripcion              |
|----------------|--------------|---------|--------------------------|
| `mcp-sap-adt`  | mcp-sap-adt  | 8001    | Servidor MCP Python      |

## Paso 3: Verificar que funciona

```bash
# Health check
curl http://localhost:8001/health

# Pool stats
curl http://localhost:8001/pool-stats
```

## Paso 4: Configurar el cliente MCP

Las credenciales SAP ahora se gestionan en el servidor (via variables de entorno del contenedor Docker). Los clientes MCP solo necesitan apuntar a la URL del servidor.

### 4.1 Claude Code (CLI)

El fichero `.mcp.json` ya esta incluido en el proyecto:

```json
{
  "mcpServers": {
    "sap-adt": {
      "type": "http",
      "url": "http://localhost:8001/mcp/"
    }
  }
}
```

Al abrir Claude Code desde el directorio del proyecto, detectara el `.mcp.json` automaticamente:

```bash
cd local_mcp_server
claude
```

Verificar con el comando `/mcp` dentro de Claude Code que el servidor aparece en la lista.

### 4.2 Claude Desktop

Localizar el fichero de configuracion:

| Sistema Operativo | Ruta                                                          |
|--------------------|---------------------------------------------------------------|
| **Windows**        | `%APPDATA%\Claude\claude_desktop_config.json`                 |
| **macOS**          | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| **Linux**          | `~/.config/Claude/claude_desktop_config.json`                 |

Crear o editar `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "sap-adt": {
      "url": "http://localhost:8001/mcp/"
    }
  }
}
```

Reiniciar Claude Desktop para que cargue la nueva configuracion.

### 4.3 Alternativa: modo interactivo

Si por algun motivo el servidor no tiene credenciales configuradas, el agente de IA puede
conectar usando el tool `connect_to_sap` pasando las credenciales como parametros.

## Comandos utiles

```bash
# Ver logs en tiempo real
docker compose logs -f

# Parar el servidor
docker compose down

# Reconstruir tras cambios en el codigo
docker compose up --build -d

# Ver estado del contenedor
docker compose ps
```

## Arquitectura de red

```
Cliente MCP (Claude Desktop, Claude Code, etc.)
    │
    │  HTTP :8001
    ▼
┌─────────────────────────────────────────┐
│  Docker Container                       │
│  (credenciales SAP en env vars)         │
│                                         │
│  mcp-sap-adt (FastMCP + Python)         │
│    │                                    │
└────│────────────────────────────────────┘
     │
     │  HTTPS (Basic Auth + CSRF)
     ▼
  SAP System (ADT REST API)
```

## Troubleshooting

### El servidor no arranca

```bash
# Ver logs de arranque
docker compose logs mcp-sap-adt

# Verificar que el health check pasa
docker compose ps
```

### No se puede conectar a SAP

- Verificar que el hostname SAP es accesible desde el contenedor
- Verificar que el puerto ADT esta abierto (normalmente 443 o 8000)
- Comprobar credenciales SAP (usuario, password, client)
- Revisar logs: `docker compose logs -f mcp-sap-adt`
