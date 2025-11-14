# @tag: scripts,powershell,test

$ErrorActionPreference = 'Stop'
Import-Module "$PSScriptRoot\LabControl.psm1" -Force -Verbose
Get-Command -Name '*-LabJob' -CommandType Function
