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
├── nginx/
│   ├── nginx.conf              # Configuracion del reverse proxy
│   ├── certs/
│   │   ├── server.crt          # Certificado TLS (ya generado, valido 1 ano)
│   │   └── server.key          # Clave privada TLS
│   └── generate-certs.sh       # Script para regenerar certificados si expiran
├── Dockerfile                  # Imagen del servidor MCP
├── docker-compose.yml          # Orquestacion: servidor MCP + nginx con TLS
├── .env                        # Variables de entorno (crear a partir de .env.example)
├── .env.example                # Plantilla de variables de entorno
└── .dockerignore               # Exclusiones del build context
```

## Paso 1: Crear el fichero .env

```bash
cp .env.example .env
```

Editar `.env` si se necesitan variables adicionales.

## Paso 2: Levantar los servicios

```bash
docker compose up --build -d
```

Esto arranca:

| Servicio          | Contenedor        | Puerto externo | Descripcion                          |
|-------------------|-------------------|----------------|--------------------------------------|
| `mcp-sap-adt`  | mcp-sap-adt    | Ninguno        | Servidor MCP Python (solo red interna) |
| `nginx`           | sap-mcp-nginx     | 443 (HTTPS)    | Reverse proxy con TLS                |

## Paso 3: Verificar que funciona

```bash
# Health check
curl -k https://localhost/health

# Pool stats
curl -k https://localhost/pool-stats
```

> La flag `-k` es necesaria porque el certificado es self-signed.

## Paso 4: Configurar Claude Desktop

### 4.1 Localizar el fichero de configuracion

El fichero de configuracion de Claude Desktop se encuentra en:

| Sistema Operativo | Ruta                                                          |
|--------------------|---------------------------------------------------------------|
| **Windows**        | `%APPDATA%\Claude\claude_desktop_config.json`                 |
| **macOS**          | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| **Linux**          | `~/.config/Claude/claude_desktop_config.json`                 |

Si el directorio no existe, crearlo:

```bash
# Windows (PowerShell)
mkdir "$env:APPDATA\Claude"

# macOS / Linux
mkdir -p ~/.config/Claude
```

### 4.2 Crear o editar el fichero

Crear `claude_desktop_config.json` con el siguiente contenido:

```json
{
  "mcpServers": {
    "sap-adt": {
      "url": "https://localhost/mcp/",
      "headers": {
        "x-hostname": "<SAP_SYSTEM_URL>",
        "x-username": "<SAP_USERNAME>",
        "x-password": "<SAP_PASSWORD>",
        "x-client": "110"
      }
    }
  }
}
```

### 4.3 Reemplazar los placeholders

| Placeholder        | Valor                                                        | Ejemplo                              |
|--------------------|--------------------------------------------------------------|--------------------------------------|
| `<SAP_SYSTEM_URL>` | URL completa del sistema SAP (protocolo + host + puerto)     | `https://sap-dev.company.com:8000`   |
| `<SAP_USERNAME>`   | Tu usuario SAP                                               | `MGARCIA`                            |
| `<SAP_PASSWORD>`   | Tu password SAP                                              | `mi_password`                        |
| `110`              | Numero de cliente SAP (cambiar si es diferente)              | `110`, `120`, `300`, `310`           |

### 4.4 Reiniciar Claude Desktop

Cerrar y volver a abrir Claude Desktop para que cargue la nueva configuracion.
Al iniciar, deberia aparecer el servidor MCP `sap-adt` disponible con todas sus tools.

### Alternativa: sin headers (modo interactivo)

Si el cliente MCP no soporta headers custom, el agente de IA puede
conectar usando el tool `connect_to_sap` pasando las credenciales como parametros.
En este caso dejar los headers vacios y pedir al agente: "conectate a SAP".

## Paso 5: Configurar Claude Code (CLI)

Si usas Claude Code (la CLI) en lugar de Claude Desktop, la configuracion es diferente.

### 5.1 Crear el fichero `.mcp.json` en la raiz del proyecto

```json
{
  "mcpServers": {
    "sap-adt": {
      "type": "http",
      "url": "https://localhost/mcp/",
      "headers": {
        "x-hostname": "<SAP_SYSTEM_URL>",
        "x-username": "<SAP_USERNAME>",
        "x-password": "${SAP_PASSWORD}",
        "x-client": "110"
      }
    }
  }
}
```

> **Nota:** A diferencia de Claude Desktop, Claude Code requiere el campo `"type": "http"` en la configuracion del servidor.

### 5.2 Configurar la variable de entorno para la password

Claude Code soporta la sintaxis `${VAR_NAME}` para expandir variables de entorno en `.mcp.json`. Esto permite no almacenar la password en el fichero.

**Windows (CMD) - temporal:**

```cmd
set SAP_PASSWORD=tu_password
claude
```

**Windows (PowerShell) - temporal:**

```powershell
$env:SAP_PASSWORD = "tu_password"
claude
```

**Windows - permanente:**

Ir a Panel de Control > Sistema > Configuracion avanzada del sistema > Variables de entorno y crear `SAP_PASSWORD` como variable de usuario.

**Linux / macOS - temporal:**

```bash
export SAP_PASSWORD=tu_password
claude
```

**Linux / macOS - permanente:**

Anadir al `~/.bashrc` o `~/.zshrc`:

```bash
export SAP_PASSWORD=tu_password
```

### 5.3 Reemplazar los placeholders

Los mismos placeholders que en el Paso 4.3 (`<SAP_SYSTEM_URL>`, `<SAP_USERNAME>`, etc.), excepto `<SAP_PASSWORD>` que se resuelve via variable de entorno.

### 5.4 Iniciar Claude Code

Al abrir Claude Code desde el directorio del proyecto, deberia detectar el `.mcp.json` y preguntar si se quiere aprobar el servidor MCP.

```bash
cd local_mcp_server
claude
```

Verificar con el comando `/mcp` dentro de Claude Code que el servidor aparece en la lista.

## Comandos utiles

```bash
# Ver logs en tiempo real
docker compose logs -f

# Ver logs solo del servidor MCP
docker compose logs -f mcp-sap-adt

# Ver logs solo de nginx
docker compose logs -f nginx

# Parar todo
docker compose down

# Reconstruir tras cambios en el codigo
docker compose up --build -d

# Ver estado de los contenedores
docker compose ps
```

## Certificados TLS

Los certificados self-signed ya estan generados en `nginx/certs/` y son validos por 1 ano (hasta febrero 2027).

### Regenerar certificados (cuando expiren)

```bash
cd nginx
bash generate-certs.sh
docker compose restart nginx
```

### Usar certificados propios (produccion)

Reemplazar los ficheros en `nginx/certs/`:

```
nginx/certs/server.crt   -> tu certificado
nginx/certs/server.key   -> tu clave privada
```

Y reiniciar nginx:

```bash
docker compose restart nginx
```

## Arquitectura de red

```
Cliente MCP (Claude Desktop, VS Code, etc.)
    │
    │  HTTPS :443  (credenciales SAP cifradas en headers)
    ▼
┌─────────────────────────────────────────┐
│  Docker Network                         │
│                                         │
│  nginx (TLS termination)                │
│    │                                    │
│    │  HTTP :8001 (red interna)          │
│    ▼                                    │
│  mcp-sap-adt (FastMCP + Python)      │
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

### nginx da error de certificado

```bash
# Verificar que los certificados existen
ls nginx/certs/

# Verificar validez del certificado
openssl x509 -in nginx/certs/server.crt -noout -dates
```

### No se puede conectar a SAP

- Verificar que el hostname SAP es accesible desde el contenedor
- Verificar que el puerto ADT esta abierto (normalmente 443 o 8000)
- Comprobar credenciales SAP (usuario, password, client)
- Revisar logs: `docker compose logs -f mcp-sap-adt`
