<#
.SYNOPSIS
    Sample search harness that uses SearchToolkit presets to sweep TODOs.

.DESCRIPTION
    Imports scripts/powershell/SearchToolkit.psm1 relative to this file and
    runs the "repo-todos" preset. Pass -DryRun to preview filters without
    executing Select-String. Logs land in logs/search-history.jsonl by default.

.EXAMPLE
    pwsh -ExecutionPolicy Bypass -File scripts/powershell/examples/find-todos.ps1

.EXAMPLE
    pwsh -File scripts/powershell/examples/find-todos.ps1 -DryRun
#>
[CmdletBinding()]
param(
    [switch]$DryRun,
    [switch]$NoLog
)

$modulePath = Join-Path $PSScriptRoot ".." "SearchToolkit.psm1" | Resolve-Path
Import-Module $modulePath -Force

Invoke-RepoSearch -Preset repo-todos -EmitStats -DryRun:$DryRun.IsPresent -NoLog:$NoLog.IsPresent
