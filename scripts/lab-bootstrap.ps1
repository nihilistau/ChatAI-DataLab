#requires -Version 7.0
<#
    Lab bootstrapper that:
      1. Establishes repo-wide global variables for key paths and interpreters.
      2. Performs lightweight "deep scan" validation of notebooks, backend, frontend, and DataLab assets.
      3. Activates virtual environments long enough to confirm they are healthy.
      4. Imports LabControl, displays the dashboard, and launches backend/frontend/datalab jobs.

    Usage:
        pwsh -ExecutionPolicy Bypass -File .\scripts\lab-bootstrap.ps1
        pwsh -ExecutionPolicy Bypass -File .\scripts\lab-bootstrap.ps1 -SkipScan -NoLaunch
#>
[CmdletBinding()]
param(
    [switch]$SkipScan,
    [switch]$NoLaunch
)

Set-StrictMode -Version Latest

function Write-LabInfo {
    param([Parameter(Mandatory)][string]$Message,[ConsoleColor]$Color = [ConsoleColor]::Cyan)
    $previous = [Console]::ForegroundColor
    [Console]::ForegroundColor = $Color
    Write-Host $Message
    [Console]::ForegroundColor = $previous
}

function Assert-LabPath {
    param([Parameter(Mandatory)][string]$Label,[Parameter(Mandatory)][string]$Path)
    if (-not (Test-Path $Path)) {
        throw "Missing $Label path: $Path"
    }
}

function Get-LabPythonCandidate {
    param([string[]]$CandidatePaths)
    foreach ($path in $CandidatePaths) {
        if ($path -and (Test-Path $path)) { return $path }
    }
    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCmd) { return $pythonCmd.Path }
    throw "Python interpreter not found. Install python3 or create the project virtual environments first."
}

function Test-LabNotebooks {
    param([string]$NotebookRoot)
    if (-not (Test-Path $NotebookRoot)) { return }
    $issues = @()
    Get-ChildItem -Path $NotebookRoot -Filter *.ipynb -Recurse | ForEach-Object {
        try {
            $_ | Get-Content -Raw | ConvertFrom-Json | Out-Null
        } catch {
            $issues += "{0}: {1}" -f $_.FullName, $_.Exception.Message
        }
    }
    if ($issues.Count -gt 0) {
        $issuesText = $issues -join [Environment]::NewLine
        throw "Notebook validation failed:`n$issuesText"
    }
}

function Invoke-LabSyntaxScan {
    Write-LabInfo "[scan] Validating notebook JSON..."
    Test-LabNotebooks -NotebookRoot $global:LabNotebookRoot

    Write-LabInfo "[scan] Compiling backend sources..."
    $backendInterpreter = if ($IsWindows) {
        Join-Path $global:LabBackendEnv "Scripts\\python.exe"
    } else {
        Join-Path $global:LabBackendEnv "bin/python"
    }
    $backendPy = Get-LabPythonCandidate -CandidatePaths @($backendInterpreter)
    Push-Location $global:LabBackend
    try {
        & $backendPy -m compileall -q .
        if ($LASTEXITCODE -ne 0) {
            throw "python compileall failed for backend"
        }
    } finally { Pop-Location }

    Write-LabInfo "[scan] Compiling DataLab scripts..."
    $datalabInterpreter = if ($IsWindows) {
        Join-Path $global:LabDatalabEnv "Scripts\\python.exe"
    } else {
        Join-Path $global:LabDatalabEnv "bin/python"
    }
    $labPy = Get-LabPythonCandidate -CandidatePaths @($global:LabPyKernel, $datalabInterpreter)
    Push-Location $global:LabDatalab
    try {
        & $labPy -m compileall -q scripts
        if ($LASTEXITCODE -ne 0) {
            throw "python compileall failed for datalab/scripts"
        }
    } finally { Pop-Location }

    Write-LabInfo "[scan] Checking frontend configs..."
    $frontendConfigs = @("package.json", "tsconfig.json", "vite.config.ts")
    foreach ($config in $frontendConfigs) {
        $full = Join-Path $global:LabFrontend $config
        Assert-LabPath -Label "frontend config" -Path $full
        if ($config -like "*.json") {
            try {
                Get-Content -Raw -Path $full | ConvertFrom-Json | Out-Null
            } catch {
                $message = "Invalid JSON in {0}: {1}" -f $full, $_.Exception.Message
                throw $message
            }
        }
    }
}

function Initialize-LabVirtualEnv {
    param(
        [Parameter(Mandatory)][string]$EnvPath,
        [Parameter(Mandatory)][string]$Label
    )
    if (-not (Test-Path $EnvPath)) {
        Write-Warning "$Label environment not found at $EnvPath"
        return
    }
    $activate = if ($IsWindows) { Join-Path $EnvPath "Scripts\\Activate.ps1" } else { Join-Path $EnvPath "bin/activate" }
    if (-not (Test-Path $activate)) {
        Write-Warning "Activation script for $Label missing at $activate"
        return
    }
    Write-LabInfo "[env] Activating $Label" ([ConsoleColor]::Green)
    if ($IsWindows) {
        . $activate
    } else {
        . $activate
    }
    try {
        & python --version
    } finally {
        if (Get-Command deactivate -ErrorAction SilentlyContinue) {
            deactivate
        }
    }
}

# --- Path discovery ---------------------------------------------------------
$global:LabRoot = (Resolve-Path (Join-Path $PSScriptRoot ".." )).Path
$global:LabScripts = Join-Path $global:LabRoot "scripts"
$global:PShell = Join-Path $global:LabScripts "powershell"
$global:LabBackend = Join-Path $global:LabRoot "chatai\backend"
$global:LabBackendEnv = Join-Path $global:LabBackend ".venv"
$global:LabFrontend = Join-Path $global:LabRoot "chatai\frontend"
$global:LabFrontendEnv = Join-Path $global:LabFrontend "node_modules"
$global:LabDatalab = Join-Path $global:LabRoot "datalab"
$global:LabNotebookRoot = Join-Path $global:LabDatalab "notebooks"
$global:LabDatalabEnv = Join-Path $global:LabDatalab ".venv"
$global:LabPyKernel = if ($IsWindows) {
    Join-Path $global:LabDatalabEnv "Scripts\\python.exe"
} else {
    Join-Path $global:LabDatalabEnv "bin/python"
}
$global:py_kernal = $global:LabPyKernel  # user-requested alias

# Export as environment variables for downstream shells/jobs.
Set-Item -Path Env:LAB_ROOT -Value $global:LabRoot
Set-Item -Path Env:LAB_BACKEND -Value $global:LabBackend
Set-Item -Path Env:LAB_FRONTEND -Value $global:LabFrontend
Set-Item -Path Env:LAB_DATALAB -Value $global:LabDatalab
Set-Item -Path Env:LAB_PY_KERNEL -Value $global:LabPyKernel
Set-Variable -Name PShell -Value $global:PShell -Scope Global -Force

# Ensure downstream Python invocations load repo-level sitecustomize helpers.
$pathSeparator = [IO.Path]::PathSeparator
$desiredEntries = @($global:LabRoot)
if ($env:PYTHONPATH) {
    $desiredEntries += $env:PYTHONPATH -split [IO.Path]::PathSeparator
}
$env:PYTHONPATH = ($desiredEntries | Where-Object { $_ -and $_.Trim() } | Select-Object -Unique) -join $pathSeparator
Write-LabInfo "[env] PYTHONPATH = $($env:PYTHONPATH)"

Write-LabInfo "[paths] LabRoot = $($global:LabRoot)"
Write-LabInfo "[paths] PShell  = $($global:PShell)"

Assert-LabPath -Label "LabControl module" -Path (Join-Path $global:PShell "LabControl.psm1")
Assert-LabPath -Label "scripts folder" -Path $global:LabScripts
Assert-LabPath -Label "backend" -Path $global:LabBackend
Assert-LabPath -Label "frontend" -Path $global:LabFrontend
Assert-LabPath -Label "datalab" -Path $global:LabDatalab

if (-not $SkipScan) {
    Invoke-LabSyntaxScan
}

Initialize-LabVirtualEnv -EnvPath $global:LabBackendEnv -Label "backend"
Initialize-LabVirtualEnv -EnvPath $global:LabDatalabEnv -Label "datalab"

Import-Module (Join-Path $global:PShell "LabControl.psm1") -Force
Invoke-LabControlCenter

if (-not $NoLaunch) {
    Write-LabInfo "[jobs] Starting backend/front/datalab via LabControl..." ([ConsoleColor]::Green)
    Start-LabJob -Name backend -Force | Out-Null
    Start-LabJob -Name frontend -Force | Out-Null
    Start-LabJob -Name datalab -Force | Out-Null
    Show-LabJobs
}

Write-LabInfo "Bootstrap complete." ([ConsoleColor]::Green)
