# @tag: scripts,powershell,lab-control

Set-StrictMode -Version Latest

$script:LabControlState = @{
    Root      = (Resolve-Path (Join-Path $PSScriptRoot ".." "..")).Path
    JobPrefix = "Lab:"
}
$script:LabControlState["BackupDir"] = Join-Path $script:LabControlState.Root "backups"
$script:LabControlState["Groups"] = @{
    backend     = Join-Path $script:LabControlState.Root "chatai\backend"
    frontend    = Join-Path $script:LabControlState.Root "chatai\frontend"
    datalab     = Join-Path $script:LabControlState.Root "datalab"
    scripts     = Join-Path $script:LabControlState.Root "scripts"
    controlplane= Join-Path $script:LabControlState.Root "controlplane"
    data        = Join-Path $script:LabControlState.Root "data"
}

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
    $defs.datalab = [ordered]@{
        Name             = "datalab"
        DisplayName      = "DataLab Jupyter"
        WorkingDirectory = Join-Path $root "datalab"
        Command          = "jupyter lab --ip=0.0.0.0 --no-browser"
        Environment      = @{}
        Type             = "python"
        VirtualEnvPath   = Join-Path (Join-Path $root "datalab") ".venv"
    }
    $defs.tail = [ordered]@{
        Name             = "tail"
        DisplayName      = "Tail Log Monitor"
        WorkingDirectory = $root
        Command          = "Get-Content -Path .\\data\\interactions.db -Wait"
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
        return Start-Job -Name $jobName -InitializationScript { Set-StrictMode -Version Latest } -ScriptBlock $sb -ArgumentList $script
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
        [string[]]$Include = @("chatai", "datalab", "data", "scripts")
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
        [ValidateSet("backend", "frontend", "datalab", "all")]
        [string]$Target = "all"
    )
    $root = Get-LabRoot
    $targets = if ($Target -eq "all") { @("backend", "frontend", "datalab") } else { @($Target) }
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
            "datalab" {
                Push-Location (Join-Path $root "datalab")
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
    Save-LabWorkspace -Destination $Output -Include @("chatai", "datalab", "data") | Out-Null
    Write-Host "Release package ready at $Output"
    return $Output
}

function Invoke-LabControlCenter {
    [CmdletBinding()]
    param()
    $root = Get-LabRoot
    Write-Host "ChatAI · DataLab Control Center" -ForegroundColor Cyan
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

Export-ModuleMember -Function *-Lab*
