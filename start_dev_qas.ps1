<#
.SYNOPSIS
    Arranca dos servidores MCP SAP ADT en paralelo: desarrollo y calidad.

.DESCRIPTION
    Levanta dos contenedores independientes (mcp-sap-adt-dev y mcp-sap-adt-qas),
    cada uno con sus propias credenciales SAP y su propio puerto en el host.
    Los tools MCP son los mismos en ambos; lo que cambia es el sistema SAP destino.

    Usa su propio proyecto de Docker Compose (sap-mcp-dev-qas), asi que no
    interfiere con el contenedor de un solo entorno que arranca start.ps1.

.EXAMPLE
    ./start_dev_qas.ps1 -Username "mgarcia" -Password "tu_password"

.EXAMPLE
    ./start_dev_qas.ps1 -Username "mgarcia" -Password "tu_password" -Build

.EXAMPLE
    # Usuario, client o host distintos por entorno
    ./start_dev_qas.ps1 -DevUsername "mgarcia" -DevPassword "pass_des" -QasUsername "mgarcia_q" -QasPassword "pass_cal" -QasClient "200"

.EXAMPLE
    ./start_dev_qas.ps1 -Down
#>
[CmdletBinding()]
param(
    # Credenciales comunes a ambos entornos (sobrescribibles por entorno)
    [string]$Username,
    [string]$Password,
    [string]$Client = "100",

    # Desarrollo (DS4)
    [string]$DevHostname = "https://vhmtjds4ci.fra3.sap.torres.es:20400/",
    [string]$DevUsername,
    [string]$DevPassword,
    [string]$DevClient,
    [int]$DevPort = 8001,

    # Calidad (QS4)
    [string]$QasHostname = "https://vhmtjqs4ci.fra3.sap.torres.es:20400/",
    [string]$QasUsername,
    [string]$QasPassword,
    [string]$QasClient,
    [int]$QasPort = 8002,

    # Acciones
    [switch]$Build,
    [switch]$Down,
    [switch]$Status,
    [switch]$Logs
)

# Los ejecutables nativos (docker) escriben su progreso en stderr; con "Stop"
# PowerShell lo trataria como error terminante y abortaria el build a medias.
$ErrorActionPreference = "Continue"

$ComposeFile   = Join-Path $PSScriptRoot "docker-compose.dev-qas.yml"
$ProjectName   = "sap-mcp-dev-qas"
$ComposeArgs   = @("compose", "-f", $ComposeFile, "-p", $ProjectName)
$OwnContainers = @("mcp-sap-adt-dev", "mcp-sap-adt-qas")

function Remove-EnvVar([string]$Name) {
    if (Test-Path "Env:$Name") { Remove-Item "Env:$Name" }
}

function Clear-SapEnv {
    foreach ($prefix in @("DEV", "QAS")) {
        foreach ($suffix in @("SAP_HOSTNAME", "SAP_USERNAME", "SAP_PASSWORD", "SAP_CLIENT", "PORT")) {
            Remove-EnvVar "${prefix}_${suffix}"
        }
    }
}

# ps / logs / down no usan las credenciales, pero compose avisa de cada variable
# sin definir. Se rellenan con un placeholder para que la salida quede limpia.
function Set-PlaceholderEnv {
    foreach ($prefix in @("DEV", "QAS")) {
        foreach ($suffix in @("SAP_HOSTNAME", "SAP_USERNAME", "SAP_PASSWORD")) {
            if (-not (Test-Path "Env:${prefix}_${suffix}")) {
                Set-Item "Env:${prefix}_${suffix}" "unused"
            }
        }
    }
}

# Devuelve una descripcion de quien ocupa el puerto, o $null si esta disponible.
# Un contenedor propio no cuenta como conflicto: compose lo recrea sin problema.
function Get-PortConflict([int]$Port) {
    $holders = @(docker ps --filter "publish=$Port" --format "{{.Names}}" 2>$null | Where-Object { $_ })
    $foreign = @($holders | Where-Object { $OwnContainers -notcontains $_ })
    if ($foreign.Count -gt 0) {
        return ("el contenedor Docker " + ($foreign -join ", "))
    }
    if ($holders.Count -gt 0) { return $null }

    # Nota: TcpListener NO detecta los bindings de Docker Desktop en Windows;
    # Get-NetTCPConnection si. Solo existe en Windows, de ahi el guard.
    if (-not (Get-Command Get-NetTCPConnection -ErrorAction SilentlyContinue)) { return $null }
    $listening = @()
    try {
        $listening = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction Stop)
    }
    catch {
        return $null
    }
    if ($listening.Count -gt 0) {
        $holderPid = $listening[0].OwningProcess
        $proc = Get-Process -Id $holderPid -ErrorAction SilentlyContinue
        if ($proc) { return ("el proceso {0} (PID {1})" -f $proc.ProcessName, $holderPid) }
        return ("el proceso con PID {0}" -f $holderPid)
    }
    return $null
}

# --- Comprobacion de Docker ---
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Error "Docker no esta instalado o no esta en el PATH."
    exit 1
}
docker info --format "{{.ServerVersion}}" | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Error "Docker no responde. Arranca Docker Desktop y vuelve a intentarlo."
    exit 1
}

# --- Acciones que no necesitan credenciales ---
if ($Down) {
    Write-Host "Parando los servidores MCP (desarrollo + calidad)..." -ForegroundColor Yellow
    Set-PlaceholderEnv
    try { & docker @ComposeArgs down }
    finally { Clear-SapEnv }
    exit $LASTEXITCODE
}

if ($Status) {
    Set-PlaceholderEnv
    try { & docker @ComposeArgs ps }
    finally { Clear-SapEnv }
    exit $LASTEXITCODE
}

if ($Logs) {
    Set-PlaceholderEnv
    try { & docker @ComposeArgs logs -f }
    finally { Clear-SapEnv }
    exit $LASTEXITCODE
}

# --- Resolucion de credenciales por entorno ---
if (-not $DevUsername) { $DevUsername = $Username }
if (-not $DevPassword) { $DevPassword = $Password }
if (-not $DevClient)   { $DevClient   = $Client }
if (-not $QasUsername) { $QasUsername = $Username }
if (-not $QasPassword) { $QasPassword = $Password }
if (-not $QasClient)   { $QasClient   = $Client }

$missing = @()
if (-not $DevUsername) { $missing += "usuario de desarrollo (-Username o -DevUsername)" }
if (-not $DevPassword) { $missing += "password de desarrollo (-Password o -DevPassword)" }
if (-not $QasUsername) { $missing += "usuario de calidad (-Username o -QasUsername)" }
if (-not $QasPassword) { $missing += "password de calidad (-Password o -QasPassword)" }
if ($missing.Count -gt 0) {
    Write-Error ("Faltan credenciales: " + ($missing -join ", "))
    exit 1
}

if ($DevPort -eq $QasPort) {
    Write-Error "-DevPort y -QasPort no pueden ser el mismo puerto ($DevPort)."
    exit 1
}

# --- Pre-flight: los puertos del host deben estar libres ---
$conflict = $false
foreach ($target in @(
    @{ Name = "desarrollo"; Port = $DevPort },
    @{ Name = "calidad";    Port = $QasPort }
)) {
    $holder = Get-PortConflict $target.Port
    if ($holder) {
        Write-Host ("El puerto {0} ({1}) ya esta ocupado por {2}." -f $target.Port, $target.Name, $holder) -ForegroundColor Red
        $conflict = $true
    }
}
if ($conflict) {
    Write-Host ""
    Write-Host "Opciones:" -ForegroundColor Yellow
    Write-Host "  - Parar el servidor de un solo entorno:  docker compose down"
    Write-Host "  - Usar otros puertos:                    ./start_dev_qas.ps1 ... -DevPort 8011 -QasPort 8012"
    exit 1
}

# --- Arranque ---
$env:DEV_SAP_HOSTNAME = $DevHostname
$env:DEV_SAP_USERNAME = $DevUsername
$env:DEV_SAP_PASSWORD = $DevPassword
$env:DEV_SAP_CLIENT   = $DevClient
$env:DEV_PORT         = $DevPort

$env:QAS_SAP_HOSTNAME = $QasHostname
$env:QAS_SAP_USERNAME = $QasUsername
$env:QAS_SAP_PASSWORD = $QasPassword
$env:QAS_SAP_CLIENT   = $QasClient
$env:QAS_PORT         = $QasPort

$exitCode = 1
try {
    $upArgs = $ComposeArgs + @("up", "-d")
    if ($Build) { $upArgs += "--build" }

    Write-Host "Arrancando servidores MCP SAP ADT..." -ForegroundColor Cyan
    & docker @upArgs
    $exitCode = $LASTEXITCODE
}
finally {
    Clear-SapEnv
}

if ($exitCode -ne 0) {
    Write-Error "El arranque ha fallado (exit $exitCode). Revisa los logs con: ./start_dev_qas.ps1 -Logs"
    exit $exitCode
}

Write-Host ""
Write-Host "Servidores arrancados:" -ForegroundColor Green
Write-Host ("  DESARROLLO  mcp-sap-adt-dev  http://localhost:{0}/mcp/   {1} (client {2}, user {3})" -f $DevPort, $DevHostname, $DevClient, $DevUsername)
Write-Host ("  CALIDAD     mcp-sap-adt-qas  http://localhost:{0}/mcp/   {1} (client {2}, user {3})" -f $QasPort, $QasHostname, $QasClient, $QasUsername)
Write-Host ""
Write-Host "Configuracion para el cliente MCP (.mcp.json):" -ForegroundColor Cyan
Write-Host @"
{
  "mcpServers": {
    "sap-adt-dev": { "type": "http", "url": "http://localhost:$DevPort/mcp/" },
    "sap-adt-qas": { "type": "http", "url": "http://localhost:$QasPort/mcp/" }
  }
}
"@
Write-Host ""
Write-Host "Utiles:" -ForegroundColor Cyan
Write-Host "  ./start_dev_qas.ps1 -Status      estado de los contenedores"
Write-Host "  ./start_dev_qas.ps1 -Logs        logs de ambos en tiempo real"
Write-Host "  ./start_dev_qas.ps1 -Down        parar ambos"
