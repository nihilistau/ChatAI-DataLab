# @tag: scripts,powershell,lab-control

param(
    [switch]$ControlCenter
)

$modulePath = Join-Path $PSScriptRoot "powershell\LabControl.psm1"
Import-Module $modulePath -Force

if ($ControlCenter) {
    Invoke-LabControlCenter
}
