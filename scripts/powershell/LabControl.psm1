# @tag: scripts,powershell,lab-control

Set-StrictMode -Version Latest

$script:LabControlState = @{
    Root      = (Resolve-Path (Join-Path $PSScriptRoot ".." "..")).Path
    JobPrefix = "Lab:"
}
$script:LabControlState["BackupDir"] = Join-Path $script:LabControlState.Root "backups"
$script:LabControlState["Groups"] = @{
    backend      = Join-Path $script:LabControlState.Root "chatai\backend"
    frontend     = Join-Path $script:LabControlState.Root "chatai\frontend"
    kitchen      = Join-Path $script:LabControlState.Root "kitchen"
    scripts      = Join-Path $script:LabControlState.Root "scripts"
    controlplane = Join-Path $script:LabControlState.Root "controlplane"
    data         = Join-Path $script:LabControlState.Root "data"
}
$script:LabControlState["SearchToolkitPath"] = Join-Path $PSScriptRoot "SearchToolkit.psm1"

function Get-LabRoot {
    [CmdletBinding()]
    param()
    return $script:LabControlState.Root
}

function Get-LabGroupPath {
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$Name)
    $groups = $script:LabControlState.Groups
    if ($groups.ContainsKey($Name)) {
        return $groups[$Name]
    }
    $candidate = Join-Path (Get-LabRoot) $Name
    if (Test-Path $candidate) {
        return $candidate
    }
    throw "Unknown group '$Name'."
}

function Get-LabPythonCommand {
    [CmdletBinding()]
    param()
    return Get-LabExecutablePath -Names @("python", "python3") -Require -ErrorAction Stop
}

function Get-LabPipPath {
    param([Parameter(Mandatory)][string]$ProjectPath)
    $venvDir = Join-Path $ProjectPath ".venv"
    if ($IsWindows) {
        return Join-Path $venvDir "Scripts\pip.exe"
    }
    return Join-Path $venvDir "bin/pip"
}

function Get-LabUnixScriptPath {
    $scriptPath = Join-Path (Get-LabRoot) "scripts\labctl.sh"
    if (-not (Test-Path $scriptPath)) {
        throw "Linux control script not found at $scriptPath"
    }
    return $scriptPath
}

function Get-LabDiagnosticsDirectory {
    $dir = Join-Path (Get-LabRoot) "data\logs"
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    return $dir
}

function Get-LabDiagnosticsPath {
    param([string]$Name = "lab-diagnostics.jsonl")
    return Join-Path (Get-LabDiagnosticsDirectory) $Name
}

function Write-LabDiagnosticRecord {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$Category,
        [Parameter(Mandatory)][string]$Message,
        [hashtable]$Data
    )
    $record = [ordered]@{
        timestamp = (Get-Date).ToString('o')
        category  = $Category
        message   = $Message
        data      = $Data ?? @{}
    }
    $json = $record | ConvertTo-Json -Depth 10
    $path = Get-LabDiagnosticsPath
    $json | Out-File -FilePath $path -Encoding utf8 -Append
    return $path
}

function ConvertTo-WslPath {
    param([Parameter(Mandatory)][string]$Path)
    $wsl = Get-Command wsl.exe -ErrorAction SilentlyContinue
    if (-not $wsl) { return $null }
    $resolved = Convert-Path $Path
    $converted = & wsl.exe wslpath -a -- $resolved
    if ($LASTEXITCODE -ne 0) { return $null }
    return $converted.Trim()
}

function Invoke-LabUnixControl {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory, Position = 0, ValueFromRemainingArguments = $true)]
        [string[]]$Arguments,
        [ValidateSet("Auto", "WSL", "Bash")]
        [string]$Shell = "Auto",
        [string]$Distribution,
        [switch]$PassThru
    )
    $root = Get-LabRoot
    Get-LabUnixScriptPath | Out-Null
    $executionResult = $null

    $invokeWslLabctl = {
        param([string[]]$CommandArgs)
        $wslPath = ConvertTo-WslPath -Path $root
        if (-not $wslPath) { return $null }
        $params = @()
        if ($Distribution) {
            $params += '-d'
            $params += $Distribution
        }
        $params += '--cd'
        $params += $wslPath
        $params += '--'
        $params += './scripts/labctl.sh'
        $params += $CommandArgs
        return & wsl.exe @params 2>&1
    }

    $invokeBashLabctl = {
        param([string[]]$CommandArgs)
        $bash = Get-Command bash -ErrorAction SilentlyContinue
        if (-not $bash) { return $null }
        $escapedArgs = $CommandArgs | ForEach-Object { "'" + ($_ -replace "'", "'\''") + "'" }
        $argString = $escapedArgs -join ' '
        $cmd = "cd '$root'; ./scripts/labctl.sh $argString"
        return & $bash.Path -lc $cmd 2>&1
    }

    switch ($Shell) {
        "WSL" { $executionResult = & $invokeWslLabctl -CommandArgs $Arguments }
        "Bash" { $executionResult = & $invokeBashLabctl -CommandArgs $Arguments }
        default {
            $executionResult = & $invokeWslLabctl -CommandArgs $Arguments
            if (-not $executionResult) {
                $executionResult = & $invokeBashLabctl -CommandArgs $Arguments
            }
        }
    }

    if (-not $executionResult) {
        throw "Unable to locate WSL or bash to run labctl.sh. Install Windows Subsystem for Linux or Git Bash."
    }

    if ($LASTEXITCODE -ne 0) {
        $joined = $executionResult -join [Environment]::NewLine
        throw "labctl failed: $joined"
    }

    if ($PassThru) {
        return $executionResult
    }

    $executionResult | ForEach-Object { Write-Host $_ }
}

function Get-LabJobDefinitions {
    [CmdletBinding()]
    param()
    if ($script:LabControlState.ContainsKey("JobDefinitions")) {
        return $script:LabControlState.JobDefinitions
    }

    $root = Get-LabRoot
    $defs = [ordered]@{}
    $backendPath = Join-Path (Join-Path $root "chatai") "backend"
    $defs.backend = [ordered]@{
        Name             = "backend"
        DisplayName      = "ChatAI FastAPI"
        WorkingDirectory = $backendPath
        Command          = "uvicorn main:app --reload --host 0.0.0.0 --port 8000"
        Environment      = @{ PYTHONPATH = $backendPath }
        Type             = "python"
        VirtualEnvPath   = Join-Path $backendPath ".venv"
    }
    $defs.frontend = [ordered]@{
        Name             = "frontend"
        DisplayName      = "ChatAI Vite"
        WorkingDirectory = Join-Path (Join-Path $root "chatai") "frontend"
        Command          = "npm run dev -- --host"
        Environment      = @{}
        Type             = "node"
    }
    $defs.kitchen = [ordered]@{
        Name             = "kitchen"
        DisplayName      = "Kitchen Jupyter"
        WorkingDirectory = Join-Path $root "kitchen"
        Command          = "jupyter lab --ip=0.0.0.0 --no-browser"
        Environment      = @{}
        Type             = "python"
        VirtualEnvPath   = Join-Path (Join-Path $root "kitchen") ".venv"
    }
    $defs.tail = [ordered]@{
        Name             = "tail"
        DisplayName      = "Tail Log Monitor"
        WorkingDirectory = $root
        Command          = "python scripts\playground_store.py tail-log --follow --limit 40"
        Environment      = @{}
        Type             = "utility"
    }

    $script:LabControlState.JobDefinitions = $defs
    return $defs
}

function Resolve-LabJobDefinition {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$Name
    )
    $defs = Get-LabJobDefinitions
    if (-not $defs.Contains($Name)) {
        throw "Unknown job '$Name'. Available jobs: $($defs.Keys -join ', ')"
    }
    return $defs[$Name]
}

function New-LabJobScript {
    param(
        [Parameter(Mandatory)]$Definition
    )
    $envInject = @()
    foreach ($pair in $Definition.Environment.GetEnumerator()) {
        $envInject += "$($pair.Key)=$($pair.Value)"
    }
    return [pscustomobject]@{
        WorkingDirectory = $Definition.WorkingDirectory
        Command          = $Definition.Command
        EnvironmentPairs = $envInject
        VirtualEnvPath   = $Definition.VirtualEnvPath
    }
}

function Get-LabJobName {
    param([string]$Name)
    return "$($script:LabControlState.JobPrefix)$Name"
}

function Start-LabJob {
    [CmdletBinding(SupportsShouldProcess)]
    param(
        [Parameter(Mandatory)][string]$Name,
        [switch]$Force
    )
    $jobName = Get-LabJobName $Name
    $existing = Get-Job -Name $jobName -ErrorAction SilentlyContinue
    if ($existing -and -not $Force) {
        Write-Verbose "Job $Name already running. Use -Force to restart."
        return $existing
    }
    if ($existing -and $Force) {
        Stop-LabJob -Name $Name -Force
        Remove-Job -Name $jobName -Force -ErrorAction SilentlyContinue
    }

    $def = Resolve-LabJobDefinition -Name $Name
    $script = New-LabJobScript -Definition $def
    $sb = {
        param($script)
        Set-Location $script.WorkingDirectory
        if ($script.VirtualEnvPath -and (Test-Path $script.VirtualEnvPath)) {
            $isWindowsRuntime = $env:OS -like '*Windows*'
            if ($isWindowsRuntime) {
                $activate = Join-Path $script.VirtualEnvPath "Scripts\Activate.ps1"
                if (Test-Path $activate) {
                    . $activate
                }
            } else {
                $activate = Join-Path $script.VirtualEnvPath "bin/activate"
                if (Test-Path $activate) {
                    . $activate
                }
            }
        }
        foreach ($pair in $script.EnvironmentPairs) {
            $key, $value = $pair -split "=", 2
            if ($key) { Set-Item -Path "Env:$key" -Value $value }
        }
        Invoke-Expression $script.Command
    }

    if ($PSCmdlet.ShouldProcess($Name, "Start job")) {
        $job = Start-Job -Name $jobName -InitializationScript { Set-StrictMode -Version Latest } -ScriptBlock $sb -ArgumentList $script
        Write-LabDiagnosticRecord -Category 'lab-job' -Message 'Job started' -Data @{ name = $Name; command = $script.Command }
        return $job
    }
}

function Stop-LabJob {
    [CmdletBinding(SupportsShouldProcess)]
    param(
        [Parameter(Mandatory)][string]$Name,
        [switch]$Force
    )
    $jobName = Get-LabJobName $Name
    $job = Get-Job -Name $jobName -ErrorAction SilentlyContinue
    if (-not $job) {
        Write-Verbose "Job $Name not found"
        return
    }
        if ($PSCmdlet.ShouldProcess($Name, "Stop job")) {
            if ($Force) {
                Stop-Job -Job $job -Force -ErrorAction SilentlyContinue
            } else {
                Stop-Job -Job $job -ErrorAction SilentlyContinue
            }
            Write-LabDiagnosticRecord -Category 'lab-job' -Message 'Job stopped' -Data @{ name = $Name; forced = [bool]$Force }
        }
}

function Restart-LabJob {
    [CmdletBinding(SupportsShouldProcess)]
    param(
        [Parameter(Mandatory)][string]$Name
    )
    if ($PSCmdlet.ShouldProcess($Name, "Restart job")) {
        Stop-LabJob -Name $Name -Force
        Start-LabJob -Name $Name -Force
    }
}

function Start-AllLabJobs {
    [CmdletBinding()]
    param()
    $defs = Get-LabJobDefinitions
    foreach ($name in $defs.Keys) {
        Start-LabJob -Name $name -Verbose:$false | Out-Null
    }
}

function Stop-AllLabJobs {
    [CmdletBinding()]
    param([switch]$Force)
    $jobs = Get-Job -Name "$($script:LabControlState.JobPrefix)*" -ErrorAction SilentlyContinue
    foreach ($job in $jobs) {
        $name = $job.Name.Replace($script:LabControlState.JobPrefix, "")
        Stop-LabJob -Name $name -Force:$Force
    }
}

function Restart-AllLabJobs {
    [CmdletBinding()]
    param()
    Stop-AllLabJobs -Force
    Start-AllLabJobs
}

function Show-LabJobs {
    [CmdletBinding()]
    param()
    $jobs = Get-Job -Name "$($script:LabControlState.JobPrefix)*" -ErrorAction SilentlyContinue
    if (-not $jobs) {
        Write-Host "No lab jobs are active." -ForegroundColor Yellow
        return
    }
    $jobs | Select-Object Name, State, HasMoreData, PSBeginTime, PSEndTime | Format-Table -AutoSize
}

function Test-LabHealth {
    [CmdletBinding()]
    param(
        [string]$StatusUrl = "http://localhost:8000/api/control/status",
        [switch]$Json
    )
    $root = Get-LabRoot
    $python = Get-LabPythonCommand
    $scriptPath = Join-Path $root "scripts\control_health.py"
    if (-not (Test-Path $scriptPath)) {
        throw "control_health.py not found at $scriptPath"
    }
    $arguments = @($scriptPath, '--status-url', $StatusUrl)
    if ($Json) { $arguments += '--json' }
    $env:LAB_ROOT = $root
    & $python @arguments
    $exitCode = $LASTEXITCODE
    if ($exitCode -eq 0) {
        Write-LabDiagnosticRecord -Category 'healthcheck' -Message 'Lab health verified' -Data @{ statusUrl = $StatusUrl }
    } else {
        Write-LabDiagnosticRecord -Category 'healthcheck' -Message 'Lab health degraded' -Data @{ statusUrl = $StatusUrl; exitCode = $exitCode }
        throw "Health check failed with exit code $exitCode"
    }
}

function Get-LabJobSnapshot {
    [CmdletBinding()]
    param()
    $defs = Get-LabJobDefinitions
    $results = @()
    foreach ($entry in $defs.GetEnumerator()) {
        $jobName = Get-LabJobName $entry.Key
        $job = Get-Job -Name $jobName -ErrorAction SilentlyContinue
        $state = if ($job) { $job.State.ToString() } else { "Stopped" }
        $results += [pscustomobject]@{
            Name        = $entry.Key
            DisplayName = $entry.Value.DisplayName
            State       = $state
            StartedAt   = if ($job) { $job.PSBeginTime } else { $null }
            Runtime     = "windows"
            Command     = $entry.Value.Command
        }
    }
    return $results
}

function Receive-LabJobOutput {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$Name,
        [switch]$Keep
    )
    $jobName = Get-LabJobName $Name
    $job = Get-Job -Name $jobName -ErrorAction Stop
    Receive-Job -Job $job -Keep:$Keep
}

function Remove-LabJob {
    [CmdletBinding(SupportsShouldProcess)]
    [Alias("Kill-LabJob")]
    param([Parameter(Mandatory)][string]$Name)
    $jobName = Get-LabJobName $Name
    if ($PSCmdlet.ShouldProcess($Name, "Remove job")) {
        Stop-LabJob -Name $Name -Force
        Remove-Job -Name $jobName -Force -ErrorAction SilentlyContinue
    }
}

function Save-LabWorkspace {
    [CmdletBinding()]
    param(
    [string]$Destination = (Join-Path -Path $script:LabControlState.BackupDir -ChildPath ("workspace-{0}.zip" -f (Get-Date -Format "yyyyMMdd-HHmmss"))),
        [string[]]$Include = @("chatai", "kitchen", "data", "scripts")
    )
    $root = Get-LabRoot
    if (-not (Test-Path -Path (Split-Path $Destination -Parent))) {
        New-Item -ItemType Directory -Path (Split-Path $Destination -Parent) -Force | Out-Null
    }
    $paths = @()
    foreach ($item in $Include) {
        $target = Join-Path $root $item
        if (Test-Path $target) { $paths += $target }
    }
    Compress-Archive -Path $paths -DestinationPath $Destination -Force
    Write-Host "Workspace backup saved to $Destination"
    return $Destination
}

function Restore-LabWorkspace {
    [CmdletBinding(SupportsShouldProcess)]
    param(
        [Parameter(Mandatory)][string]$ArchivePath,
        [switch]$Overwrite
    )
    $root = Get-LabRoot
    if (-not (Test-Path $ArchivePath)) {
        throw "Archive $ArchivePath not found"
    }
    if ($PSCmdlet.ShouldProcess($ArchivePath, "Restore workspace")) {
        if ($Overwrite) {
            Expand-Archive -LiteralPath $ArchivePath -DestinationPath $root -Force
        } else {
            Expand-Archive -LiteralPath $ArchivePath -DestinationPath $root
        }
    }
}

function Install-LabDependencies {
    [CmdletBinding()]
    param(
        [ValidateSet("backend", "frontend", "kitchen", "all")]
        [string]$Target = "all"
    )
    $root = Get-LabRoot
    $targets = if ($Target -eq "all") { @("backend", "frontend", "kitchen") } else { @($Target) }
    $pythonCmd = Get-LabPythonCommand
    foreach ($item in $targets) {
        switch ($item) {
            "backend" {
                Push-Location (Join-Path (Join-Path $root "chatai") "backend")
                try {
                    & $pythonCmd -m venv .venv | Out-Null
                    $pipPath = Get-LabPipPath -ProjectPath (Get-Location).Path
                    & $pipPath install --upgrade pip
                    & $pipPath install -r requirements.txt
                } finally { Pop-Location }
            }
            "frontend" {
                Push-Location (Join-Path (Join-Path $root "chatai") "frontend")
                try {
                    npm install
                    npm run build
                } finally { Pop-Location }
            }
            "kitchen" {
                Push-Location (Join-Path $root "kitchen")
                try {
                    & $pythonCmd -m venv .venv | Out-Null
                    $pipPath = Get-LabPipPath -ProjectPath (Get-Location).Path
                    & $pipPath install --upgrade pip
                    & $pipPath install -r requirements.txt
                } finally { Pop-Location }
            }
        }
    }
}

function New-LabPackage {
    [CmdletBinding()]
    param(
    [string]$Output = (Join-Path -Path $script:LabControlState.BackupDir -ChildPath ("release-{0}.zip" -f (Get-Date -Format "yyyyMMdd-HHmmss")))
    )
    Install-LabDependencies -Target frontend
    Push-Location (Join-Path (Join-Path (Get-LabRoot) "chatai") "backend")
    try {
        pytest
    } finally { Pop-Location }
    Save-LabWorkspace -Destination $Output -Include @("chatai", "kitchen", "data") | Out-Null
    Write-Host "Release package ready at $Output"
    return $Output
}

function Invoke-LabControlCenter {
    [CmdletBinding()]
    param()
    $root = Get-LabRoot
    Write-Host "ChatAI · Kitchen Control Center" -ForegroundColor Cyan
    Write-Host ("Root: {0}" -f $root)
    Write-Host "--- Jobs ---" -ForegroundColor DarkCyan
    Show-LabJobs
    Write-Host "--- Key Commands ---" -ForegroundColor DarkCyan
    $shortcuts = @(
        "Start-LabJob -Name backend",
        "Start-AllLabJobs",
        "Stop-AllLabJobs -Force",
        "Restart-LabJob -Name frontend",
        "Save-LabWorkspace",
        "Restore-LabWorkspace -ArchivePath backups\\workspace-*.zip -Overwrite",
        "Install-LabDependencies -Target backend",
        "List-Commands -Status succeeded -Limit 5",
        "Invoke-LabSearch -Preset repo-todos",
        "Get-LabSearchPresets | Format-Table name, description",
        "Publish-LabRelease -Version 1.0.0 -DryRun",
        "New-LabPackage"
    )
    foreach ($shortcut in $shortcuts) {
        Write-Host $shortcut
    }
    Write-Host "--- Linux / Remote Automation ---" -ForegroundColor DarkCyan
    $linuxExamples = @(
        "./scripts/labctl.sh status",
        "./scripts/labctl.sh start-all",
        "./scripts/labctl.sh remote user@host start backend",
        "Invoke-LabUnixControl status"
    )
    foreach ($example in $linuxExamples) {
        Write-Host $example
    }
}

function List-LabCommands {
    [CmdletBinding()]
    param(
        [string]$ApiUrl = "http://localhost:8000/api/commands",
        [string]$StorePath = "data\\commands.json",
        [ValidateSet("never-run","running","succeeded","failed")]
        [string]$Status,
        [string]$Tag,
        [ValidateRange(1,500)]
        [int]$Limit = 50,
        [switch]$Raw
    )

    $root = Get-LabRoot
    $query = @{}
    if ($Status) { $query.status = $Status }
    if ($Tag) { $query.tag = $Tag }
    if ($Limit) { $query.limit = [string]$Limit }

    $uri = $ApiUrl
    if ($query.Count -gt 0) {
        $qs = ($query.GetEnumerator() | ForEach-Object {
                '{0}={1}' -f $_.Key, [System.Uri]::EscapeDataString($_.Value)
            }) -join '&'
        if ($uri -match '\?') {
            $uri = "$uri&$qs"
        } else {
            $uri = "$uri?$qs"
        }
    }

    $data = $null
    try {
        $data = Invoke-RestMethod -Uri $uri -Method Get -TimeoutSec 5
    } catch {
        $store = Join-Path $root $StorePath
        if (-not (Test-Path $store)) {
            throw "Unable to query $uri and fallback store '$store' was not found. Error: $($_.Exception.Message)"
        }
        $data = Get-Content -Raw -Path $store | ConvertFrom-Json
        if ($Status) {
            $data = $data | Where-Object { $_.last_status -eq $Status }
        }
        if ($Tag) {
            $needle = $Tag.ToLowerInvariant()
            $data = $data | Where-Object { $_.tags -and ($_.tags | ForEach-Object { $_.ToLowerInvariant() }) -contains $needle }
        }
        if ($Limit) {
            $data = $data | Select-Object -Last $Limit
        }
    }

    if ($Raw) {
        return $data
    }

    return $data | Select-Object id, label, command, last_status, last_run_at, tags
}

Set-Alias -Name List-Commands -Value List-LabCommands

function Get-LabExecutablePath {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string[]]$Names,
        [string[]]$ProbePaths,
        [switch]$Require
    )
    foreach ($name in $Names) {
        $cmd = Get-Command $name -ErrorAction SilentlyContinue
        if ($cmd) { return $cmd.Path }
    }
    if ($ProbePaths) {
        foreach ($path in $ProbePaths) {
            if (Test-Path $path) { return (Resolve-Path $path).Path }
        }
    }
    if ($Require) {
        throw "Unable to locate executable. Tried: $($Names -join ', ')"
    }
    return $null
}

function Get-LabFolderList {
    [CmdletBinding()]
    param(
        [string]$Path = (Get-LabRoot),
        [switch]$Recurse
    )
    $resolved = Resolve-Path $Path -ErrorAction Stop
    $folders = Get-ChildItem -Path $resolved.Path -Directory -Recurse:$Recurse
    return $folders | Select-Object @{Name = 'Name'; Expression = { $_.Name }},
        @{Name = 'FullPath'; Expression = { $_.FullName }},
        @{Name = 'RelativePath'; Expression = { [System.IO.Path]::GetRelativePath($resolved.Path, $_.FullName) }}
}

function Get-LabFileInventory {
    [CmdletBinding()]
    param(
        [string]$Path = (Get-LabRoot),
        [string]$Filter = '*',
        [switch]$Recurse,
        [switch]$IncludeHash
    )
    $resolved = Resolve-Path $Path -ErrorAction Stop
    $files = Get-ChildItem -Path $resolved.Path -File -Filter $Filter -Recurse:$Recurse
    $results = foreach ($file in $files) {
        $relative = [System.IO.Path]::GetRelativePath($resolved.Path, $file.FullName)
        $hash = $null
        if ($IncludeHash) {
            $hash = (Get-FileHash -Path $file.FullName -Algorithm SHA256).Hash
        }
        [pscustomobject]@{
            Name         = $file.Name
            FullPath     = $file.FullName
            RelativePath = $relative
            Length       = $file.Length
            LastWrite    = $file.LastWriteTimeUtc
            Hash         = $hash
        }
    }
    return $results
}

function Find-LabFile {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$Pattern,
        [string]$Path = (Get-LabRoot),
        [switch]$First
    )
    $inventory = Get-LabFileInventory -Path $Path -Recurse
    $matchSet = $inventory | Where-Object {
        $_.Name -like $Pattern -or $_.RelativePath -like $Pattern -or $_.FullPath -like $Pattern
    }
    if ($First) {
        return $matchSet | Select-Object -First 1
    }
    return $matchSet
}

function Get-LabSearchToolkitPath {
    [CmdletBinding()]
    param()
    $path = $script:LabControlState.SearchToolkitPath
    if (-not (Test-Path $path)) {
        throw "SearchToolkit.psm1 was not found near LabControl (expected at '$path')."
    }
    return (Resolve-Path $path).Path
}

function Import-LabSearchToolkit {
    [CmdletBinding()]
    param()
    $path = Get-LabSearchToolkitPath
    $module = Get-Module -Name SearchToolkit -ErrorAction SilentlyContinue
    if (-not $module -or $module.Path -ne $path) {
        $module = Import-Module -Name $path -Force -PassThru
    }
    return $module
}

function Get-LabSearchPresets {
    [CmdletBinding()]
    param()
    Import-LabSearchToolkit | Out-Null
    $config = Get-SearchToolkitConfig
    return $config.presets
}

function Invoke-LabSearch {
    [CmdletBinding(DefaultParameterSetName = 'Preset')]
    param(
        [Parameter(ParameterSetName = 'Preset', Mandatory = $true)]
        [string]$Preset,

        [Parameter(ParameterSetName = 'Pattern', Mandatory = $true)]
        [string]$Pattern,

        [string[]]$IncludeFiles,
        [string[]]$ExcludePatterns,
        [ValidateSet('python','frontend','docs','notebooks','all')]
        [string[]]$FileProfile,
        [string]$Root,
        [switch]$Regex,
        [switch]$CaseSensitive,
        [switch]$NoRecurse,
        [switch]$IncludeVenv,
        [switch]$IncludeNodeModules,
        [switch]$IncludeStorybook,
        [switch]$IncludeGit,
        [switch]$IncludePyCache,
        [switch]$DryRun,
        [switch]$ListFiles,
        [switch]$EmitStats,
        [switch]$NoLog
    )

    Import-LabSearchToolkit | Out-Null

    $forwardKeys = @(
        'Pattern','Preset','IncludeFiles','ExcludePatterns','FileProfile','Root','Regex','CaseSensitive',
        'NoRecurse','IncludeVenv','IncludeNodeModules','IncludeStorybook','IncludeGit','IncludePyCache',
        'DryRun','ListFiles','EmitStats','NoLog'
    )

    $forward = @{}
    foreach ($key in $forwardKeys) {
        if ($PSBoundParameters.ContainsKey($key)) {
            $forward[$key] = $PSBoundParameters[$key]
        }
    }

    if (-not $forward.ContainsKey('Pattern') -and -not $forward.ContainsKey('Preset')) {
        throw "Invoke-LabSearch requires -Pattern or -Preset."
    }

    return Invoke-RepoSearch @forward
}

function Get-LabFolderSnapshot {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$Group,
        [string]$Path,
        [switch]$SkipContentHash
    )
    if (-not $Path) {
        $Path = Get-LabGroupPath -Name $Group
    }
    $resolved = Resolve-Path $Path -ErrorAction Stop
    $inventory = Get-LabFileInventory -Path $resolved.Path -Recurse -IncludeHash:(!$SkipContentHash)
    $files = $inventory | Sort-Object RelativePath | ForEach-Object {
        [pscustomobject]@{
            RelativePath = $_.RelativePath
            Length       = $_.Length
            Hash         = $_.Hash
        }
    }
    $summary = ($files | ForEach-Object {
            $hashValue = if ($null -ne $_.Hash) { $_.Hash } else { '' }
            "{0}|{1}|{2}" -f $_.RelativePath.ToLowerInvariant(), $_.Length, $hashValue
        }) -join "\n"
    $sha = [System.Security.Cryptography.SHA256]::Create()
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($summary)
    $digest = -join ($sha.ComputeHash($bytes) | ForEach-Object { $_.ToString('x2') })
    return [pscustomobject]@{
        Group     = $Group
        Root      = $resolved.Path
        CreatedAt = Get-Date
        FileCount = $files.Count
        Digest    = $digest
        Files     = $files
    }
}

function Save-LabFolderSnapshot {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$Group,
        [string]$Path,
        [string]$Destination
    )
    if (-not $Path) {
        $Path = Get-LabGroupPath -Name $Group
    }
    if (-not $Destination) {
        $integrityDir = Join-Path (Get-LabRoot) "data\integrity"
        if (-not (Test-Path $integrityDir)) {
            New-Item -ItemType Directory -Path $integrityDir -Force | Out-Null
        }
        $Destination = Join-Path $integrityDir ("{0}-{1}.json" -f $Group, (Get-Date -Format "yyyyMMdd-HHmmss"))
    }
    $snapshot = Get-LabFolderSnapshot -Group $Group -Path $Path
    $snapshot | ConvertTo-Json -Depth 6 | Set-Content -Path $Destination -Encoding UTF8
    return $Destination
}

function Test-LabFolderSnapshot {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$SnapshotPath,
        [string]$Path
    )
    if (-not (Test-Path $SnapshotPath)) {
        throw "Snapshot file $SnapshotPath not found"
    }
    $raw = Get-Content -Raw -Path $SnapshotPath | ConvertFrom-Json -Depth 6
    if (-not $Path) {
        $Path = $raw.Root
    }
    $current = Get-LabFolderSnapshot -Group $raw.Group -Path $Path -SkipContentHash:($null -eq $raw.Files[0].Hash)
    $reference = $raw.Files | Select-Object RelativePath, Hash, Length
    $latest    = $current.Files | Select-Object RelativePath, Hash, Length
    $diff = Compare-Object -ReferenceObject $reference -DifferenceObject $latest -Property RelativePath, Hash, Length -PassThru
    return [pscustomobject]@{
        Group          = $raw.Group
        SnapshotDigest = $raw.Digest
        CurrentDigest  = $current.Digest
        Matches        = ($raw.Digest -eq $current.Digest) -and (-not $diff)
        Differences    = $diff
    }
}

function Get-LabLatestVersionTag {
    [CmdletBinding()]
    param()

    $gitPath = Get-LabExecutablePath -Names @("git") -Require -ErrorAction Stop
    $root = Get-LabRoot
    Push-Location $root
    try {
        $tags = & $gitPath tag -l "v*"
    }
    finally {
        Pop-Location
    }

    $versions = @()
    foreach ($tag in $tags) {
        if (-not $tag) { continue }
        if ($tag -match '^v?(?<major>\d+)\.(?<minor>\d+)\.(?<patch>\d+)$') {
            $versions += [pscustomobject]@{
                Tag   = if ($tag -like 'v*') { $tag } else { "v$tag" }
                Major = [int]$Matches.major
                Minor = [int]$Matches.minor
                Patch = [int]$Matches.patch
            }
        }
    }

    if (-not $versions -or $versions.Count -eq 0) {
        return [pscustomobject]@{ Tag = "v0.0.0"; Major = 0; Minor = 0; Patch = 0 }
    }

    return ($versions | Sort-Object -Property Major, Minor, Patch | Select-Object -Last 1)
}

function Resolve-LabReleaseVersion {
    [CmdletBinding()]
    param(
        [string]$Version,
        [ValidateSet('patch','minor','major')]
        [string]$Bump
    )

    if ($Version) {
        return $Version
    }

    if (-not $Bump) {
        throw "Provide -Version or -Bump to determine the release tag."
    }

    $latest = Get-LabLatestVersionTag
    $major = $latest.Major
    $minor = $latest.Minor
    $patch = $latest.Patch

    switch ($Bump) {
        'major' {
            $major += 1
            $minor = 0
            $patch = 0
        }
        'minor' {
            $minor += 1
            $patch = 0
        }
        default {
            $patch += 1
        }
    }

    return "{0}.{1}.{2}" -f $major, $minor, $patch
}

function Update-LabChangelog {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$Version,
        [Parameter(Mandatory)][string]$ChangelogPath,
        [string]$TemplatePath,
        [string[]]$Sections
    )

    if (-not (Test-Path $ChangelogPath)) {
        throw "CHANGELOG not found at $ChangelogPath"
    }

    $date = Get-Date -Format 'yyyy-MM-dd'
    $entry = $null

    if ($TemplatePath -and (Test-Path $TemplatePath)) {
        $entry = Get-Content -Raw -Path $TemplatePath
        $entry = $entry.Replace('{{VERSION}}', $Version).Replace('{{DATE}}', $date)
        if (-not $entry.EndsWith([Environment]::NewLine)) {
            $entry += [Environment]::NewLine
        }
    }

    if (-not $entry) {
        $entry = "## $Version - $date" + [Environment]::NewLine + "- Describe the release" + [Environment]::NewLine + [Environment]::NewLine
    }

    if ($Sections -and $Sections.Count -gt 0) {
        foreach ($section in $Sections) {
            if ([string]::IsNullOrWhiteSpace($section)) { continue }
            $entry += "### $section" + [Environment]::NewLine + "- TODO" + [Environment]::NewLine
        }
        $entry += [Environment]::NewLine
    }
    $content = Get-Content -Raw -Path $ChangelogPath
    Set-Content -Path $ChangelogPath -Value ($entry + $content) -NoNewline
}

function Update-LabSearchTelemetry {
    [CmdletBinding()]
    param(
        [string]$LogPath = "logs\search-history.jsonl",
        [string]$SummaryPath = "data\search_telemetry.json",
        [string]$ScriptPath = "scripts\search_telemetry.py"
    )

    $root = Get-LabRoot
    $pythonCmd = Get-LabPythonCommand

    $resolvedScript = Join-Path $root $ScriptPath
    if (-not (Test-Path $resolvedScript)) {
        throw "Search telemetry script not found at $resolvedScript"
    }

    $resolvedLog = Join-Path $root $LogPath
    $resolvedSummary = Join-Path $root $SummaryPath
    $resolvedLogDir = Split-Path -Parent $resolvedLog
    if (-not (Test-Path $resolvedLogDir)) {
        New-Item -ItemType Directory -Path $resolvedLogDir -Force | Out-Null
    }
    $resolvedSummaryDir = Split-Path -Parent $resolvedSummary
    if (-not (Test-Path $resolvedSummaryDir)) {
        New-Item -ItemType Directory -Path $resolvedSummaryDir -Force | Out-Null
    }

    $commandArgs = @(
        $resolvedScript,
        "ingest",
        "--log-path", $resolvedLog,
        "--output", $resolvedSummary
    )

    & $pythonCmd @commandArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Search telemetry ingestion failed with exit code $LASTEXITCODE"
    }

    Write-Host "Search telemetry ledger written to $resolvedSummary" -ForegroundColor Green
}

function Invoke-LabSearchLibrarian {
    [CmdletBinding()]
    param(
        [string]$LogPath = "logs\search-history.jsonl",
        [int]$KeepLast = 5000,
        [int]$ArchiveOlderThanDays,
        [string]$ArchiveDirectory = "data\search-history-archive",
        [switch]$SkipArchive,
        [switch]$RunTelemetryIngestion,
        [string]$TelemetrySummaryPath = "data\search_telemetry.json",
        [string]$TelemetryScriptPath = "scripts\search_telemetry.py"
    )

    $root = Get-LabRoot
    $resolvedLog = Join-Path $root $LogPath
    if (-not (Test-Path $resolvedLog)) {
        Write-Warning "Search history log not found at $resolvedLog. Nothing to prune."
        return
    }

    $lines = Get-Content -LiteralPath $resolvedLog -ErrorAction SilentlyContinue
    if (-not $lines -or $lines.Count -eq 0) {
        Write-Host "Search history log is empty; nothing to prune." -ForegroundColor Yellow
        return
    }

    $entries = @()
    foreach ($line in $lines) {
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        try {
            $parsed = $line | ConvertFrom-Json -Depth 16
            $timestampSource = $parsed.timestamp
            if (-not $timestampSource) {
                $timestampValue = Get-Date
            }
            elseif ($timestampSource -is [DateTimeOffset]) {
                $timestampValue = $timestampSource.UtcDateTime
            }
            elseif ($timestampSource -is [DateTime]) {
                if ($timestampSource.Kind -eq [DateTimeKind]::Utc) {
                    $timestampValue = $timestampSource
                }
                else {
                    $timestampValue = $timestampSource.ToUniversalTime()
                }
            }
            else {
                $timestampValue = [DateTimeOffset]::Parse(
                    [string]$timestampSource,
                    [System.Globalization.CultureInfo]::InvariantCulture,
                    [System.Globalization.DateTimeStyles]::RoundtripKind
                ).UtcDateTime
            }
            $entries += [pscustomobject]@{ Raw = $line; Data = $parsed; Timestamp = $timestampValue }
        }
        catch {
            Write-Warning "Skipping unparseable search history line: $line"
        }
    }

    if (-not $entries -or $entries.Count -eq 0) {
        Write-Warning "Search history log could not be parsed; aborting cleanup."
        return
    }

    $entries = $entries | Sort-Object Timestamp
    $totalEntries = $entries.Count
    $archiveEntries = @()

    if ($ArchiveOlderThanDays -gt 0) {
        $cutoff = (Get-Date).AddDays(-1 * [double]$ArchiveOlderThanDays)
        $olderItems = $entries | Where-Object { $_.Timestamp -lt $cutoff }
        if ($olderItems) {
            $archiveEntries += $olderItems
            $entries = $entries | Where-Object { $_.Timestamp -ge $cutoff }
        }
    }

    if ($KeepLast -gt 0 -and $entries.Count -gt $KeepLast) {
        $excessCount = $entries.Count - $KeepLast
        $overflow = $entries | Select-Object -First $excessCount
        $archiveEntries += $overflow
        $entries = $entries | Select-Object -Skip $excessCount
    }

    $archiveEntries = $archiveEntries | Sort-Object Timestamp
    $remainingEntries = $entries | Sort-Object Timestamp
    $archivePath = $null

    if ($archiveEntries.Count -gt 0 -and -not $SkipArchive) {
        $archiveDir = Join-Path $root $ArchiveDirectory
        if (-not (Test-Path $archiveDir)) {
            New-Item -ItemType Directory -Path $archiveDir -Force | Out-Null
        }
        $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
        $archivePath = Join-Path $archiveDir "search-history-archive-$stamp.jsonl"
        $archiveContent = $archiveEntries | ForEach-Object { $_.Raw }
        Set-Content -LiteralPath $archivePath -Value $archiveContent -NoNewline:$false
    }

    if ($remainingEntries.Count -gt 0) {
        $remainingContent = $remainingEntries | ForEach-Object { $_.Raw }
        Set-Content -LiteralPath $resolvedLog -Value $remainingContent -NoNewline:$false
    }
    else {
        Clear-Content -LiteralPath $resolvedLog
    }

    if ($RunTelemetryIngestion) {
        Update-LabSearchTelemetry -LogPath $LogPath -SummaryPath $TelemetrySummaryPath -ScriptPath $TelemetryScriptPath | Out-Null
    }

    return [pscustomobject]@{
        TotalEntries     = $totalEntries
        ArchivedEntries  = $archiveEntries.Count
        RemainingEntries = $remainingEntries.Count
        ArchivePath      = $archivePath
    }
}

function Invoke-LabReleaseChecklist {
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$Script)

    if (-not (Test-Path $Script)) {
        Write-Warning "Release checklist script $Script not found; skipping."
        return
    }

    & pwsh -File $Script
    if ($LASTEXITCODE -ne 0) {
        throw "Release checklist script failed with exit code $LASTEXITCODE"
    }
}

function Invoke-LabReleasePipeline {
    [CmdletBinding()]
    param(
        [string]$Version,
        [ValidateSet('patch','minor','major')]
        [string]$Bump = 'patch',
        [switch]$Force,
        [switch]$AsJob,
        [switch]$DryRun,
        [switch]$SkipIntegrity,
        [switch]$Push,
        [switch]$FinalizeChangelog,
        [switch]$RunTests,
        [switch]$UpdateIntegrity,
        [string]$Branch = "main",
        [string]$ChangelogPath = "CHANGELOG.md",
        [string]$ChangelogTemplate,
        [string[]]$ChangelogSections,
        [string]$TagMessage
    )

    if (-not $PSBoundParameters.ContainsKey('Push')) { $Push = $true }
    if (-not $PSBoundParameters.ContainsKey('FinalizeChangelog')) { $FinalizeChangelog = $true }
    if (-not $PSBoundParameters.ContainsKey('RunTests')) { $RunTests = $true }
    if (-not $PSBoundParameters.ContainsKey('UpdateIntegrity')) { $UpdateIntegrity = $true }

    $releaseArgs = [ordered]@{ Branch = $Branch }

    if ($Version) { $releaseArgs['Version'] = $Version }
    if (-not $Version -and $Bump) { $releaseArgs['Bump'] = $Bump }
    if ($Force) { $releaseArgs['Force'] = $true }
    if ($DryRun) { $releaseArgs['DryRun'] = $true }
    if ($SkipIntegrity) { $releaseArgs['SkipIntegrity'] = $true }
    if ($Push) { $releaseArgs['Push'] = $true }
    if ($FinalizeChangelog) { $releaseArgs['FinalizeChangelog'] = $true }
    if ($RunTests) { $releaseArgs['RunTests'] = $true }
    if ($UpdateIntegrity) { $releaseArgs['UpdateIntegrity'] = $true }
    if ($ChangelogPath) { $releaseArgs['ChangelogPath'] = $ChangelogPath }
    if ($ChangelogTemplate) { $releaseArgs['ChangelogTemplate'] = $ChangelogTemplate }
    if ($ChangelogSections) { $releaseArgs['ChangelogSections'] = $ChangelogSections }
    if ($TagMessage) { $releaseArgs['TagMessage'] = $TagMessage }

    if ($AsJob) {
        $jobName = Get-LabJobName "release-pipeline"
        $modulePath = Join-Path $PSScriptRoot "LabControl.psm1"
        return Start-Job -Name $jobName -InitializationScript { Set-StrictMode -Version Latest } -ScriptBlock {
                param($modulePath, $arguments)
                Import-Module $modulePath -Force
                Publish-LabRelease @arguments
            } -ArgumentList $modulePath, $releaseArgs
    }

    return Publish-LabRelease @releaseArgs
}

function Publish-LabRelease {
    [CmdletBinding(SupportsShouldProcess)]
    param(
        [string]$Version,
        [ValidateSet('patch','minor','major')]
        [string]$Bump,
        [switch]$Push,
        [switch]$Force,
        [switch]$DryRun,
        [switch]$SkipIntegrity,
        [string]$Branch = "main",
        [string]$TagMessage,
        [switch]$FinalizeChangelog,
        [switch]$RunTests,
        [switch]$UpdateIntegrity,
        [string]$ChangelogPath = "CHANGELOG.md",
        [string]$ReleaseChecklistScript = "scripts/release_checklist.ps1",
        [string]$ChangelogTemplate,
        [string[]]$ChangelogSections
    )

    if (-not $Version -and -not $Bump) {
        throw "Publish-LabRelease requires -Version or -Bump."
    }

    $root = Get-LabRoot
    $gitPath = Get-LabExecutablePath -Names @("git") -Require
    $pythonCmd = Get-LabPythonCommand

    $resolvedVersion = Resolve-LabReleaseVersion -Version $Version -Bump $Bump
    $tagName = if ($resolvedVersion -like "v*") { $resolvedVersion } else { "v$resolvedVersion" }
    if (-not $TagMessage) {
        $TagMessage = "Framework $tagName"
    }

    $preflightIssues = @()

    Push-Location $root
    try {
        $currentBranch = (& $gitPath rev-parse --abbrev-ref HEAD).Trim()
        if ($currentBranch -ne $Branch) {
            $preflightIssues += "Current branch '$currentBranch' differs from required '$Branch'"
        }

        $statusOutput = & $gitPath status --porcelain
        $dirtyEntries = @($statusOutput | Where-Object { $_ -match '^(\?\?|[MADRCU ]{2})' })
        if ($dirtyEntries.Count -gt 0) {
            $preflightIssues += "Working tree has $($dirtyEntries.Count) change(s)"
        }

        if (-not $SkipIntegrity) {
            & $pythonCmd scripts/project_integrity.py status
            $integrityExit = $LASTEXITCODE
            if ($integrityExit -ne 0 -and -not $UpdateIntegrity) {
                $preflightIssues += "project_integrity.py status exited with $integrityExit"
            }
        }

        $existingTag = (& $gitPath tag -l $tagName)
        if ($existingTag) {
            $preflightIssues += "Tag $tagName already exists"
        }

        if ($DryRun) {
            return [pscustomobject]@{
                Tag          = $tagName
                Branch       = $currentBranch
                Push         = [bool]$Push
                IntegrityRan = (-not $SkipIntegrity)
                DirtyFiles   = $dirtyEntries.Count
                ExistingTag  = [bool]$existingTag
                Issues       = $preflightIssues
            }
        }

        if ($preflightIssues.Count -gt 0 -and -not $Force) {
            $message = "Release preflight failed:`n - " + ($preflightIssues -join "`n - ")
            throw $message
        }

        if ($FinalizeChangelog -or $RunTests -or $UpdateIntegrity) {
            Write-Verbose "Running release checklist helpers"
        }

        if ($FinalizeChangelog) {
            $changelogParams = @{ Version = $tagName; ChangelogPath = (Join-Path $root $ChangelogPath) }
            if ($ChangelogTemplate) { $changelogParams['TemplatePath'] = (Join-Path $root $ChangelogTemplate) }
            if ($ChangelogSections) { $changelogParams['Sections'] = $ChangelogSections }
            Update-LabChangelog @changelogParams
        }

        if ($RunTests) {
            Invoke-LabReleaseChecklist -Script (Join-Path $root $ReleaseChecklistScript)
        }

        if ($UpdateIntegrity) {
            & $pythonCmd scripts/project_integrity.py checkpoint --tag release --reason $tagName
        }

        if ($existingTag -and $Force) {
            & $gitPath tag -d $tagName | Out-Null
        }

        if ($PSCmdlet.ShouldProcess($tagName, "Create git tag")) {
            & $gitPath tag -a $tagName -m $TagMessage
        }

        if ($Push -and $PSCmdlet.ShouldProcess("origin", "Push $tagName and $Branch")) {
            & $gitPath push origin $Branch
            & $gitPath push origin $tagName
        }

        return [pscustomobject]@{
            Tag     = $tagName
            Branch  = $currentBranch
            Pushed  = [bool]$Push
            Message = $TagMessage
        }
    }
    finally {
        Pop-Location
    }
}

$kitchenAliasMap = @{
    'Kitchen-Job-Start'      = 'Start-LabJob'
    'Kitchen-Job-Stop'       = 'Stop-LabJob'
    'Kitchen-Job-Restart'    = 'Restart-LabJob'
    'Kitchen-Job-StartAll'   = 'Start-AllLabJobs'
    'Kitchen-Job-StopAll'    = 'Stop-AllLabJobs'
    'Kitchen-Job-RestartAll' = 'Restart-AllLabJobs'
    'Kitchen-Job-Show'       = 'Show-LabJobs'
    'Kitchen-Job-Snapshot'   = 'Get-LabJobSnapshot'
    'Kitchen-Job-Output'     = 'Receive-LabJobOutput'
    'Kitchen-Job-Remove'     = 'Remove-LabJob'
}

foreach ($alias in $kitchenAliasMap.GetEnumerator()) {
    Set-Alias -Name $alias.Key -Value $alias.Value -Scope Script
}

Export-ModuleMember -Function *-Lab* -Alias $kitchenAliasMap.Keys
