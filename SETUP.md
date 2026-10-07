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
├── docker-compose.yml          # Orquestacion de un solo entorno
├── docker-compose.dev-qas.yml  # Orquestacion de dos entornos (desarrollo + calidad)
├── start.ps1                   # Arranque de un entorno (PowerShell)
├── start_dev_qas.ps1           # Arranque de desarrollo + calidad a la vez (PowerShell)
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
MTI: https://bfwin04.torres.es:8001/
MTP: https://bfwin01.torres.es:8081/
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

## Paso 2 (alternativa): dos entornos a la vez, desarrollo y calidad

Para trabajar contra DS4 y QS4 en la misma sesion, `start_dev_qas.ps1` levanta dos
contenedores independientes, cada uno con sus credenciales y su propio puerto:

```powershell
./start_dev_qas.ps1 -Username "mgarcia" -Password "tu_password"
```

La primera vez, o tras cambiar codigo, hay que construir la imagen:

```powershell
./start_dev_qas.ps1 -Username "mgarcia" -Password "tu_password" -Build
```

Esto arranca:

| Servicio          | Contenedor      | Puerto | Sistema SAP (default)                              |
|-------------------|-----------------|--------|----------------------------------------------------|
| `mcp-sap-adt-dev` | mcp-sap-adt-dev | 8001   | DS4 - https://vhmtjds4ci.fra3.sap.torres.es:20400/ |
| `mcp-sap-adt-qas` | mcp-sap-adt-qas | 8002   | QS4 - https://vhmtjqs4ci.fra3.sap.torres.es:20400/ |

Los tools MCP son los mismos en ambos servidores; lo unico que cambia es el sistema SAP
destino. Al terminar, el script imprime el bloque de `.mcp.json` listo para copiar.

### Sobrescribir valores por entorno

`-Username`, `-Password` y `-Client` se aplican a los dos entornos. Cualquiera de los dos
puede sobrescribirlos con sus propios parametros:

| Parametro      | Default                                        | Descripcion                     |
|----------------|------------------------------------------------|---------------------------------|
| `-Username`    | (obligatorio)                                  | Usuario para ambos entornos     |
| `-Password`    | (obligatorio)                                  | Password para ambos entornos    |
| `-Client`      | `100`                                          | Client para ambos entornos      |
| `-DevHostname` | `https://vhmtjds4ci.fra3.sap.torres.es:20400/` | Host SAP de desarrollo          |
| `-DevUsername` | valor de `-Username`                           | Usuario solo en desarrollo      |
| `-DevPassword` | valor de `-Password`                           | Password solo en desarrollo     |
| `-DevClient`   | valor de `-Client`                             | Client solo en desarrollo       |
| `-DevPort`     | `8001`                                         | Puerto del host para desarrollo |
| `-QasHostname` | `https://vhmtjqs4ci.fra3.sap.torres.es:20400/` | Host SAP de calidad             |
| `-QasUsername` | valor de `-Username`                           | Usuario solo en calidad         |
| `-QasPassword` | valor de `-Password`                           | Password solo en calidad        |
| `-QasClient`   | valor de `-Client`                             | Client solo en calidad          |
| `-QasPort`     | `8002`                                         | Puerto del host para calidad    |

Ejemplo con usuario y client distintos en calidad:

```powershell
./start_dev_qas.ps1 -DevUsername "mgarcia" -DevPassword "pass_des" -QasUsername "mgarcia_q" -QasPassword "pass_cal" -QasClient "200"
```

Ejemplo apuntando calidad a otro sistema, por ejemplo MTD, y moviendo los puertos:

```powershell
./start_dev_qas.ps1 -Username "mgarcia" -Password "tu_password" -QasHostname "https://bfwin07.torres.es:1443/" -DevPort 8011 -QasPort 8012
```

### Gestionar los dos servidores

```powershell
./start_dev_qas.ps1 -Status    # estado de los dos contenedores
./start_dev_qas.ps1 -Logs      # logs de ambos en tiempo real
./start_dev_qas.ps1 -Down      # parar y eliminar ambos
```

> El puerto de desarrollo es 8001, el mismo que usa `start.ps1`, para que un `.mcp.json`
> ya existente siga valiendo. Los dos modos no pueden convivir: si el contenedor
> `mcp-sap-adt` esta arrancado, el script lo detecta antes de intentar nada y aborta.
> Hacer `docker compose down` primero, o usar `-DevPort` y `-QasPort` para moverlos.

### Linux / macOS / Git Bash

```bash
DEV_SAP_HOSTNAME="https://vhmtjds4ci.fra3.sap.torres.es:20400/" DEV_SAP_USERNAME="mgarcia" DEV_SAP_PASSWORD="tu_password" DEV_SAP_CLIENT="100" \
QAS_SAP_HOSTNAME="https://vhmtjqs4ci.fra3.sap.torres.es:20400/" QAS_SAP_USERNAME="mgarcia" QAS_SAP_PASSWORD="tu_password" QAS_SAP_CLIENT="100" \
docker compose -f docker-compose.dev-qas.yml -p sap-mcp-dev-qas up -d
```

Los puertos del host se ajustan con `DEV_PORT` y `QAS_PORT` (default 8001 y 8002).

## Paso 3: Verificar que funciona

```bash
# Health check
curl http://localhost:8001/health

# Pool stats
curl http://localhost:8001/pool-stats
```

Si has arrancado los dos entornos, comprobar tambien el de calidad:

```bash
curl http://localhost:8002/health
curl http://localhost:8002/pool-stats
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

Con los dos entornos hace falta una entrada por servidor. Los nombres (`sap-adt-dev` y
`sap-adt-qas`) son los que apareceran como prefijo de cada tool, asi que conviene que
dejen claro a que sistema apuntan:

```json
{
  "mcpServers": {
    "sap-adt-dev": {
      "type": "http",
      "url": "http://localhost:8001/mcp/"
    },
    "sap-adt-qas": {
      "type": "http",
      "url": "http://localhost:8002/mcp/"
    }
  }
}
```

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

Con los dos entornos arrancados, el `docker compose` de arriba no los ve: viven en su
propio proyecto Compose (`sap-mcp-dev-qas`). Hay que usar el script:

```powershell
./start_dev_qas.ps1 -Logs      # logs de ambos
./start_dev_qas.ps1 -Status    # estado de ambos
./start_dev_qas.ps1 -Down      # parar ambos
```

O Docker directamente, para actuar sobre uno solo:

```bash
docker logs -f mcp-sap-adt-dev
docker restart mcp-sap-adt-qas
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

Con dos entornos, cada contenedor tiene sus propias credenciales y su propio pool de
conexiones; no comparten nada mas que la imagen Docker:

```
Cliente MCP (dos servidores configurados)
    │
    ├── HTTP :8001 ──▶ mcp-sap-adt-dev ──HTTPS──▶ SAP desarrollo (DS4)
    │
    └── HTTP :8002 ──▶ mcp-sap-adt-qas ──HTTPS──▶ SAP calidad (QS4)
```

## Troubleshooting

### El servidor no arranca

```bash
# Ver logs de arranque
docker compose logs mcp-sap-adt

# Verificar que el health check pasa
docker compose ps
```

### El puerto ya esta ocupado

`start_dev_qas.ps1` comprueba los puertos antes de arrancar e indica quien los tiene.
La causa habitual es el contenedor de un solo entorno ocupando el 8001:

```powershell
docker compose down            # para el contenedor mcp-sap-adt
./start_dev_qas.ps1 -Username "mgarcia" -Password "tu_password"
```

La alternativa es mover los servidores a otros puertos, recordando actualizar el
`.mcp.json`:

```powershell
./start_dev_qas.ps1 -Username "mgarcia" -Password "tu_password" -DevPort 8011 -QasPort 8012
```

### Un entorno funciona y el otro no

Al ser contenedores separados, conviene aislar cual falla:

```bash
docker logs mcp-sap-adt-dev
docker logs mcp-sap-adt-qas

# Confirmar a que sistema apunta cada uno
docker exec mcp-sap-adt-dev sh -c 'echo $SAP_HOSTNAME $SAP_CLIENT $SAP_USERNAME'
docker exec mcp-sap-adt-qas sh -c 'echo $SAP_HOSTNAME $SAP_CLIENT $SAP_USERNAME'
```

Si las credenciales no son validas en uno de los dos sistemas, ese servidor arranca y
responde al health check igualmente: el fallo aparece al invocar un tool, no antes.

### No se puede conectar a SAP

- Verificar que el hostname SAP es accesible desde el contenedor
- Verificar que el puerto ADT esta abierto (normalmente 443 o 8000)
- Comprobar credenciales SAP (usuario, password, client)
- Revisar logs: `docker compose logs -f mcp-sap-adt`
