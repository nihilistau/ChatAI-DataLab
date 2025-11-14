# @tag: scripts,powershell,parse

param([Parameter(Mandatory)] [string]$Path)
$tokens=$null
$errors=$null
[System.Management.Automation.Language.Parser]::ParseFile($Path,[ref]$tokens,[ref]$errors) | Out-Null
foreach ($parseError in $errors) {
	Write-Host "Message: $($parseError.Message)"
	Write-Host "Line: $($parseError.Extent.StartLineNumber) Column: $($parseError.Extent.StartColumnNumber)"
	Write-Host "Snippet: $($parseError.Extent.Text)"
	Write-Host "----"
}
