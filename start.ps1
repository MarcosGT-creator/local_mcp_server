param(
    [Parameter(Mandatory=$true)]
    [string]$Hostname,

    [Parameter(Mandatory=$true)]
    [string]$Username,

    [Parameter(Mandatory=$true)]
    [string]$Password,

    [string]$Client = "100"
)

$env:SAP_HOSTNAME = $Hostname
$env:SAP_USERNAME = $Username
$env:SAP_PASSWORD = $Password
$env:SAP_CLIENT = $Client

docker compose up -d

# Clean up env vars after launch
Remove-Item Env:SAP_HOSTNAME
Remove-Item Env:SAP_USERNAME
Remove-Item Env:SAP_PASSWORD
Remove-Item Env:SAP_CLIENT
