Param(
    [switch]$Force
)

$ErrorActionPreference = "Stop"

Write-Host "[MQTT] Installing Mosquitto (Windows) ..."

function Ensure-Admin {
    $currentIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentIdentity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltinRole]::Administrator)) {
        Write-Error "Please run this script as Administrator."
        exit 1
    }
}

Ensure-Admin

function Test-Command($cmd) {
    $null = Get-Command $cmd -ErrorAction SilentlyContinue
    return $?
}

function Install-With-Winget {
    Write-Host "[MQTT] Trying winget ..."
    winget install --id Eclipse.Mosquitto --silent --accept-package-agreements --accept-source-agreements | Out-Null
}

function Install-With-Choco {
    Write-Host "[MQTT] Trying choco ..."
    if (-not (Test-Command choco)) {
        Set-ExecutionPolicy Bypass -Scope Process -Force
        iex ((New-Object System.Net.WebClient).DownloadString('https://chocolatey.org/install.ps1'))
    }
    choco install mosquitto -y --no-progress | Out-Null
}

if (Test-Command mosquitto) {
    if ($Force) { Write-Host "[MQTT] Mosquitto found, but --Force given; reinstalling." }
    else { Write-Host "[MQTT] Mosquitto already installed." }
}

if (-not (Test-Command mosquitto) -or $Force) {
    if (Test-Command winget) { Install-With-Winget }
    elseif (Test-Command choco) { Install-With-Choco }
    else { Write-Error "Neither winget nor choco available. Install Mosquitto manually."; exit 1 }
}

# Configure local-only listener
$RepoRoot = (Resolve-Path "$PSScriptRoot\..\").Path
$ConfigDir = Join-Path $RepoRoot "config"
$MosqConf = Join-Path $ConfigDir "mosquitto.conf"
if (-not (Test-Path $MosqConf)) {
    New-Item -ItemType Directory -Force -Path $ConfigDir | Out-Null
    @"
listener 1883 127.0.0.1
allow_anonymous true
persistence true
autosave_interval 1800
"@ | Set-Content -Encoding ASCII $MosqConf
}

Write-Host "[MQTT] Configuration written to $MosqConf"

Write-Host "[MQTT] You can run: mosquitto -c `"$MosqConf`" -v"

