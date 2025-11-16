# @tag: scripts,powershell,lab-control

param(
    [switch]$ControlCenter,
    [string]$SearchPreset,
    [string]$SearchPattern,
    [ValidateSet('python','frontend','docs','notebooks','all')]
    [string[]]$FileProfile,
    [switch]$Regex,
    [switch]$CaseSensitive,
    [switch]$ListFiles,
    [switch]$DryRun,
    [switch]$EmitStats,
    [switch]$NoLog,
    [switch]$IncludeVenv,
    [switch]$IncludeNodeModules,
    [switch]$IncludeStorybook,
    [switch]$IncludeGit,
    [switch]$IncludePyCache,
    [switch]$NoRecurse,
    [string]$Root,
    [string]$ReleaseVersion,
    [ValidateSet('patch','minor','major')]
    [string]$ReleaseBump,
    [switch]$ReleasePush,
    [switch]$ReleaseForce,
    [switch]$ReleaseDryRun,
    [switch]$ReleaseSkipIntegrity,
    [switch]$ReleaseFinalizeChangelog,
    [switch]$ReleaseRunTests,
    [switch]$ReleaseUpdateIntegrity,
    [switch]$ReleasePipeline,
    [switch]$ReleaseAsJob,
    [switch]$ReleaseSkipChangelog,
    [switch]$ReleaseSkipTests,
    [switch]$ReleaseSkipPush,
    [string]$ReleaseChangelogTemplate,
    [string[]]$ReleaseChangelogSection,
    [switch]$RunSearchLibrarian,
    [int]$SearchHistoryKeep,
    [int]$SearchHistoryOlderThanDays,
    [string]$SearchHistoryArchiveDir,
    [switch]$SearchHistorySkipArchive,
    [switch]$RunSearchTelemetryIngestion,
    [string]$SearchTelemetryLogPath,
    [string]$SearchTelemetryDbPath
)

$modulePath = Join-Path $PSScriptRoot "powershell\LabControl.psm1"
Import-Module $modulePath -Force

$searchRequested = $PSBoundParameters.ContainsKey('SearchPreset') -or $PSBoundParameters.ContainsKey('SearchPattern')
$telemetryRequested = $RunSearchTelemetryIngestion
$librarianRequested = $RunSearchLibrarian
$releaseRequested = $PSBoundParameters.ContainsKey('ReleaseVersion') -or $PSBoundParameters.ContainsKey('ReleaseBump') -or $ReleasePipeline

if ($searchRequested) {
    if (-not $SearchPreset -and -not $SearchPattern) {
        throw "Provide -SearchPreset or -SearchPattern when invoking lab-control.ps1."
    }

    $searchArgs = @{}
    if ($SearchPreset) { $searchArgs['Preset'] = $SearchPreset }
    if ($SearchPattern) { $searchArgs['Pattern'] = $SearchPattern }
    if ($FileProfile) { $searchArgs['FileProfile'] = $FileProfile }
    if ($Regex) { $searchArgs['Regex'] = $true }
    if ($CaseSensitive) { $searchArgs['CaseSensitive'] = $true }
    if ($ListFiles) { $searchArgs['ListFiles'] = $true }
    if ($DryRun) { $searchArgs['DryRun'] = $true }
    if ($EmitStats) { $searchArgs['EmitStats'] = $true }
    if ($NoLog) { $searchArgs['NoLog'] = $true }
    if ($IncludeVenv) { $searchArgs['IncludeVenv'] = $true }
    if ($IncludeNodeModules) { $searchArgs['IncludeNodeModules'] = $true }
    if ($IncludeStorybook) { $searchArgs['IncludeStorybook'] = $true }
    if ($IncludeGit) { $searchArgs['IncludeGit'] = $true }
    if ($IncludePyCache) { $searchArgs['IncludePyCache'] = $true }
    if ($NoRecurse) { $searchArgs['NoRecurse'] = $true }
    if ($Root) { $searchArgs['Root'] = $Root }

    Invoke-LabSearch @searchArgs | Out-Default

    if (-not $ControlCenter) {
        return
    }
}

if ($librarianRequested) {
    $librarianArgs = @{}
    if ($SearchTelemetryLogPath) { $librarianArgs['LogPath'] = $SearchTelemetryLogPath }
    if ($PSBoundParameters.ContainsKey('SearchHistoryKeep')) { $librarianArgs['KeepLast'] = $SearchHistoryKeep }
    if ($PSBoundParameters.ContainsKey('SearchHistoryOlderThanDays')) { $librarianArgs['ArchiveOlderThanDays'] = $SearchHistoryOlderThanDays }
    if ($SearchHistoryArchiveDir) { $librarianArgs['ArchiveDirectory'] = $SearchHistoryArchiveDir }
    if ($SearchHistorySkipArchive) { $librarianArgs['SkipArchive'] = $true }
    if ($SearchTelemetryDbPath) { $librarianArgs['TelemetryDatabasePath'] = $SearchTelemetryDbPath }
    if ($RunSearchTelemetryIngestion) {
        $librarianArgs['RunTelemetryIngestion'] = $true
        $telemetryRequested = $false
    }

    $librarianResult = Invoke-LabSearchLibrarian @librarianArgs
    if ($librarianResult) {
        $librarianResult | Format-List | Out-Default
    }

    if (-not $ControlCenter -and -not $searchRequested -and -not $releaseRequested -and -not $telemetryRequested) {
        return
    }
}

if ($telemetryRequested) {
    $telemetryArgs = @{}
    if ($SearchTelemetryLogPath) { $telemetryArgs['LogPath'] = $SearchTelemetryLogPath }
    if ($SearchTelemetryDbPath) { $telemetryArgs['DatabasePath'] = $SearchTelemetryDbPath }
    Update-LabSearchTelemetry @telemetryArgs | Out-Default

    if (-not $ControlCenter -and -not $releaseRequested -and -not $searchRequested) {
        return
    }
}

if ($releaseRequested) {
    $releaseArgs = @{}
    if ($ReleaseVersion) { $releaseArgs['Version'] = $ReleaseVersion }
    if ($ReleaseBump) { $releaseArgs['Bump'] = $ReleaseBump }
    if ($ReleaseForce) { $releaseArgs['Force'] = $true }
    if ($ReleaseDryRun) { $releaseArgs['DryRun'] = $true }
    if ($ReleaseSkipIntegrity) { $releaseArgs['SkipIntegrity'] = $true }
    if ($ReleaseChangelogTemplate) { $releaseArgs['ChangelogTemplate'] = $ReleaseChangelogTemplate }
    if ($ReleaseChangelogSection) { $releaseArgs['ChangelogSections'] = $ReleaseChangelogSection }

    if (-not $releaseArgs.ContainsKey('Version') -and -not $releaseArgs.ContainsKey('Bump')) {
        throw "Provide -ReleaseVersion or -ReleaseBump when publishing a release."
    }

    if ($ReleasePipeline) {
        $releaseArgs['FinalizeChangelog'] = -not $ReleaseSkipChangelog
        $releaseArgs['RunTests'] = -not $ReleaseSkipTests
        $releaseArgs['UpdateIntegrity'] = -not $ReleaseSkipIntegrity
        $releaseArgs['Push'] = -not $ReleaseSkipPush
        if ($ReleaseAsJob) { $releaseArgs['AsJob'] = $true }
        if ($ReleaseDryRun) { $releaseArgs['DryRun'] = $true }
        $releaseResult = Invoke-LabReleasePipeline @releaseArgs
    }
    else {
        if ($ReleasePush) { $releaseArgs['Push'] = $true }
        if ($ReleaseFinalizeChangelog) { $releaseArgs['FinalizeChangelog'] = $true }
        if ($ReleaseRunTests) { $releaseArgs['RunTests'] = $true }
        if ($ReleaseUpdateIntegrity) { $releaseArgs['UpdateIntegrity'] = $true }

        $releaseResult = Publish-LabRelease @releaseArgs
    }

    $releaseResult | Format-List | Out-Default

    if (-not $ControlCenter -and -not $searchRequested -and -not $telemetryRequested) {
        return
    }
}

if ($ControlCenter) {
    Invoke-LabControlCenter
}
