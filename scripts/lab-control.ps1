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
    [switch]$ReleasePush,
    [switch]$ReleaseForce,
    [switch]$ReleaseDryRun,
    [switch]$ReleaseSkipIntegrity
)

$modulePath = Join-Path $PSScriptRoot "powershell\LabControl.psm1"
Import-Module $modulePath -Force

$searchRequested = $PSBoundParameters.ContainsKey('SearchPreset') -or $PSBoundParameters.ContainsKey('SearchPattern')
$releaseRequested = $PSBoundParameters.ContainsKey('ReleaseVersion')

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

if ($releaseRequested) {
    if (-not $ReleaseVersion) {
        throw "Provide -ReleaseVersion when requesting a release publish."
    }

    $releaseArgs = @{ Version = $ReleaseVersion }
    if ($ReleasePush) { $releaseArgs['Push'] = $true }
    if ($ReleaseForce) { $releaseArgs['Force'] = $true }
    if ($ReleaseDryRun) { $releaseArgs['DryRun'] = $true }
    if ($ReleaseSkipIntegrity) { $releaseArgs['SkipIntegrity'] = $true }

    $releaseResult = Publish-LabRelease @releaseArgs
    $releaseResult | Format-List | Out-Default

    if (-not $ControlCenter -and -not $searchRequested) {
        return
    }
}

if ($ControlCenter) {
    Invoke-LabControlCenter
}
