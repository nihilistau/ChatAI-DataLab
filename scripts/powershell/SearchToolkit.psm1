$script:ModuleRoot = Split-Path -Parent $PSCommandPath
$script:RepoRoot = (Resolve-Path (Join-Path $script:ModuleRoot "..\..")).ProviderPath
$script:ConfigPath = Join-Path $script:ModuleRoot "search-presets.json"
$script:LogDirectory = Join-Path $script:RepoRoot "logs"
$script:LogPath = Join-Path $script:LogDirectory "search-history.jsonl"

function Get-SearchToolkitConfig {
    [CmdletBinding()]
    param(
        [string]$Path = $script:ConfigPath
    )

    if (-not (Test-Path -Path $Path)) {
        throw "Search preset config not found at '$Path'."
    }

    $raw = Get-Content -Path $Path -Raw -ErrorAction Stop
    return ($raw | ConvertFrom-Json -Depth 10)
}

function Get-SearchPreset {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [string]$Name,
        [object]$Config
    )

    if (-not $Config) {
        $Config = Get-SearchToolkitConfig
    }

    $preset = $Config.presets | Where-Object { $_.name -ieq $Name } | Select-Object -First 1
    if (-not $preset) {
        throw "Preset '$Name' was not found in search-presets.json."
    }
    return $preset
}

function Get-SearchHistory {
    [CmdletBinding()]
    param(
        [int]$Last = 15,
        [switch]$Raw
    )

    if (-not (Test-Path -Path $script:LogPath)) {
        Write-Verbose "No search history has been recorded yet."
        return @()
    }

    $lines = Get-Content -Path $script:LogPath -ErrorAction Stop
    if ($Last -gt 0) {
        $lines = $lines | Select-Object -Last $Last
    }

    if ($Raw) {
        return $lines
    }

    return $lines | ForEach-Object { $_ | ConvertFrom-Json }
}

function Invoke-RepoSearch {
    [CmdletBinding(DefaultParameterSetName = 'byPattern')]
    param(
        [Parameter(ParameterSetName = 'byPattern')]
        [string]$Pattern,

        [Parameter(ParameterSetName = 'byPreset')]
        [string]$Preset,

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

    $config = Get-SearchToolkitConfig
    $presetConfig = $null

    if ($PSCmdlet.ParameterSetName -eq 'byPreset') {
        $presetConfig = Get-SearchPreset -Name $Preset -Config $config
        if (-not $Pattern) {
            $Pattern = $presetConfig.pattern
        }
    }

    if (-not $Pattern) {
        throw "You must provide a -Pattern or choose a -Preset."
    }

    $effectiveIncludes = @()

    if ($IncludeFiles) {
        $effectiveIncludes = $IncludeFiles
    } elseif ($FileProfile) {
        foreach ($profile in $FileProfile) {
            if ($profile -eq 'all') {
                $effectiveIncludes = @()
                break
            }
            $set = $config.extensionSets.$profile
            if ($set) {
                $effectiveIncludes += $set
            }
        }
    } elseif ($presetConfig.includeFiles) {
        $effectiveIncludes = $presetConfig.includeFiles
    } else {
        $effectiveIncludes = $config.defaults.includeFiles
    }

    if ($effectiveIncludes -and $effectiveIncludes.Count -eq 1 -and $effectiveIncludes[0] -eq '*') {
        $effectiveIncludes = @()
    }

    if ($effectiveIncludes) {
        $effectiveIncludes = $effectiveIncludes | Select-Object -Unique
    }

    $resolvedRoot = Resolve-SearchRoot -RequestedPath $Root -PresetRoot $presetConfig.root -DefaultRoot $config.defaults.root

    $recursive = $true
    if ($NoRecurse) {
        $recursive = $false
    } elseif ($presetConfig.recursive -ne $null) {
        $recursive = [bool]$presetConfig.recursive
    } elseif ($config.defaults.recursive -ne $null) {
        $recursive = [bool]$config.defaults.recursive
    }

    $autoExclude = @()
    if (-not $IncludeVenv) { $autoExclude += @("\\.venv", "datalab\\venv") }
    if (-not $IncludeNodeModules) { $autoExclude += "node_modules" }
    if (-not $IncludeStorybook) { $autoExclude += "storybook" }
    if (-not $IncludeGit) { $autoExclude += "\\.git" }
    if (-not $IncludePyCache) { $autoExclude += "__pycache__" }

    $effectiveExclude = @()
    $effectiveExclude += $config.defaults.excludePatterns
    if ($presetConfig.excludePatterns) { $effectiveExclude += $presetConfig.excludePatterns }
    if ($ExcludePatterns) { $effectiveExclude += $ExcludePatterns }
    $effectiveExclude += $autoExclude
    $effectiveExclude = $effectiveExclude | Where-Object { $_ } | Select-Object -Unique

    $gciParams = @{ Path = $resolvedRoot; File = $true }
    if ($recursive) { $gciParams["Recurse"] = $true }
    if ($effectiveIncludes -and $effectiveIncludes.Count -gt 0) {
        $gciParams["Include"] = $effectiveIncludes
    }

    $files = Get-ChildItem @gciParams
    if ($effectiveExclude.Count -gt 0) {
        $files = $files | Where-Object { -not (Test-PathMatchesPattern -Path $_.FullName -Patterns $effectiveExclude) }
    }

    if ($ListFiles) {
        return $files | Select-Object FullName, Length, LastWriteTime
    }

    if ($DryRun) {
            $dryRunData = @{
            Pattern = $Pattern
            Root = $resolvedRoot
            Recursive = $recursive
            IncludeFiles = $effectiveIncludes
            ExcludePatterns = $effectiveExclude
            PendingFiles = $files.Count
            } | ConvertTo-Json -Depth 4
            Write-Information -MessageData $dryRunData -InformationAction Continue
        return
    }

    if (-not $files -or $files.Count -eq 0) {
        Write-Information "No files matched the requested filters." -InformationAction Continue
        return
    }

    $selectParams = @{
        Path = $files.FullName
        Pattern = $Pattern
    }

    if ($CaseSensitive) {
        $selectParams["CaseSensitive"] = $true
    }

    if (-not $Regex) {
        $selectParams["SimpleMatch"] = $true
    }

    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $results = Select-String @selectParams
    $sw.Stop()

    $matchCount = if ($results) { $results.Count } else { 0 }
    $fileCount = if ($files) { $files.Count } else { 0 }

    $summary = [pscustomobject]@{
        Pattern = $Pattern
        Preset = $Preset
        Root = $resolvedRoot
        FilesScanned = $fileCount
        Matches = $matchCount
        DurationMs = $sw.ElapsedMilliseconds
    }

    if ($EmitStats) {
        $statsText = $summary | Format-Table -AutoSize | Out-String
        Write-Information -MessageData $statsText -InformationAction Continue
    }

    if (-not $NoLog) {
        Write-SearchLog -Entry (@{
            timestamp = (Get-Date).ToString('o')
            pattern = $Pattern
            preset = $Preset
            regex = [bool]$Regex
            caseSensitive = [bool]$CaseSensitive
            root = $resolvedRoot
            recursive = $recursive
            includeFiles = $effectiveIncludes
            excludePatterns = $effectiveExclude
            filesScanned = $fileCount
            matches = $matchCount
            durationMs = $sw.ElapsedMilliseconds
        })
    }

    if ($results) {
        return $results | Select-Object FileName, LineNumber, Line, Path
    } else {
        Write-Information "No matches found." -InformationAction Continue
    }
}

function Resolve-SearchRoot {
    param(
        [string]$RequestedPath,
        [string]$PresetRoot,
        [string]$DefaultRoot
    )

    $candidate = $null

    if ($RequestedPath) {
        $candidate = $RequestedPath
    } elseif ($PresetRoot) {
        $candidate = $PresetRoot
    } elseif ($DefaultRoot) {
        $candidate = $DefaultRoot
    } else {
        $candidate = $script:RepoRoot
    }

    if ($candidate -and -not [System.IO.Path]::IsPathRooted($candidate)) {
        $moduleRelative = Join-Path $script:ModuleRoot $candidate
        $repoRelative = Join-Path $script:RepoRoot $candidate

        if (Test-Path -Path $moduleRelative) {
            $candidate = $moduleRelative
        } elseif (Test-Path -Path $repoRelative) {
            $candidate = $repoRelative
        }
    }

    if (-not (Test-Path -Path $candidate)) {
        $candidate = Join-Path $script:ModuleRoot $candidate
    }

    if (-not (Test-Path -Path $candidate)) {
        $candidate = Join-Path $script:RepoRoot $candidate
    }

    if (-not (Test-Path -Path $candidate)) {
        throw "Unable to resolve root path '$candidate'."
    }

    return (Resolve-Path -Path $candidate).ProviderPath
}

function Test-PathMatchesPattern {
    param(
        [string]$Path,
        [string[]]$Patterns
    )

    if (-not $Patterns -or $Patterns.Count -eq 0) {
        return $false
    }

    foreach ($pattern in $Patterns) {
        if ([string]::IsNullOrWhiteSpace($pattern)) {
            continue
        }
        if ($Path -match $pattern) {
            return $true
        }
    }
    return $false
}

function Write-SearchLog {
    param(
        [hashtable]$Entry
    )

    if (-not $Entry) { return }

    if (-not (Test-Path -Path $script:LogDirectory)) {
        New-Item -ItemType Directory -Path $script:LogDirectory | Out-Null
    }

    $json = ($Entry | ConvertTo-Json -Depth 6 -Compress)
    $json | Add-Content -Path $script:LogPath
}

Export-ModuleMember -Function Invoke-RepoSearch, Get-SearchPreset, Get-SearchToolkitConfig, Get-SearchHistory
