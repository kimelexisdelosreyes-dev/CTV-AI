$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$BackendDir = Join-Path $Root "backend"
$FrontendDir = Join-Path $Root "frontend\enterprise-ui"
$LogDir = Join-Path $Root "logs"
$FrontendPort = 3001
$BackendPort = 8000

function Get-PrivateLanIPv4 {
    $addresses = Get-NetIPConfiguration |
        Where-Object {
            $_.IPv4DefaultGateway -and
            (-not $_.NetAdapter -or $_.NetAdapter.Status -eq "Up") -and
            $_.InterfaceAlias -notmatch "Docker|WSL|Hyper-V|vEthernet|Virtual|Loopback|VPN|Tailscale|WireGuard"
        } |
        ForEach-Object {
            $alias = $_.InterfaceAlias
            $_.IPv4Address | ForEach-Object {
                [pscustomobject]@{
                    InterfaceAlias = $alias
                    IPAddress = $_.IPAddress
                }
            }
        } |
        Where-Object {
            $_.IPAddress -match "^(10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[0-1])\.)"
        }

    if (-not $addresses) {
        throw "No active private LAN IPv4 address with a default gateway was found."
    }

    return $addresses | Select-Object -First 1
}

function Test-PortListening {
    param([int]$Port)
    $connection = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    return $null -ne $connection
}

function Start-LoggedPowerShell {
    param(
        [string]$Name,
        [string]$WorkingDirectory,
        [string]$Command,
        [string]$LogPath
    )

    $errorLogPath = [System.IO.Path]::ChangeExtension($LogPath, ".err.log")
    Start-Process powershell.exe -WindowStyle Hidden -WorkingDirectory $WorkingDirectory -ArgumentList @(
        "-NoExit",
        "-ExecutionPolicy", "Bypass",
        "-Command",
        "`$ErrorActionPreference='Stop'; $Command"
    ) -RedirectStandardOutput $LogPath -RedirectStandardError $errorLogPath | Out-Null
    Write-Host "Started $Name. Logs: $LogPath, $errorLogPath"
}

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$lan = Get-PrivateLanIPv4
$lanIp = $lan.IPAddress

Write-Host "Detected LAN IP: $lanIp ($($lan.InterfaceAlias))"

if (Get-Command docker -ErrorAction SilentlyContinue) {
    Write-Host "Starting Docker internal dependencies..."
    docker compose -f (Join-Path $Root "docker\compose.yml") up -d postgres qdrant
} else {
    Write-Host "Docker was not found in PATH. Skipping Docker dependency startup."
}

$corsOrigins = "http://127.0.0.1:$FrontendPort,http://localhost:$FrontendPort,http://$lanIp`:$FrontendPort"
$backendUrl = "http://127.0.0.1:$BackendPort"

if (Test-PortListening -Port $BackendPort) {
    Write-Host "Backend port $BackendPort is already listening; not starting another backend."
} else {
    $backendLog = Join-Path $LogDir "lan-backend.log"
    $backendCommand = "`$env:CORS_ALLOWED_ORIGINS='$corsOrigins'; .\start.ps1"
    Start-LoggedPowerShell -Name "backend" -WorkingDirectory $BackendDir -Command $backendCommand -LogPath $backendLog
}

if (Test-PortListening -Port $FrontendPort) {
    Write-Host "Frontend port $FrontendPort is already listening; not starting another frontend."
} else {
    $frontendLog = Join-Path $LogDir "lan-frontend.log"
    $frontendCommand = "`$env:CTV_BACKEND_URL='$backendUrl'; npm run dev"
    Start-LoggedPowerShell -Name "frontend" -WorkingDirectory $FrontendDir -Command $frontendCommand -LogPath $frontendLog
}

Write-Host ""
Write-Host "Local URL: http://127.0.0.1:$FrontendPort"
Write-Host "LAN URL: http://$lanIp`:$FrontendPort"
Write-Host "Backend health: http://$lanIp`:$BackendPort/api/v1/health"
Write-Host ""
Write-Host "If another laptop cannot connect, run the firewall commands in docs\LAN_ACCESS.md from an Administrator PowerShell."
