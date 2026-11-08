[CmdletBinding(SupportsShouldProcess = $true)]
param([Parameter(Mandatory = $true)][string]$ServerDirectory, [Parameter(Mandatory = $true)][string]$BackupDirectory)
. (Join-Path $PSScriptRoot 'cs15content.common.ps1')
$ServerDirectory = (Resolve-Path -LiteralPath $ServerDirectory).Path
$BackupDirectory = (Resolve-Path -LiteralPath $BackupDirectory).Path
$backupParent = (Get-CS15ContentPath $ServerDirectory '_content/backups').TrimEnd('\') + '\'
if (-not $BackupDirectory.StartsWith($backupParent,[StringComparison]::OrdinalIgnoreCase)) { throw 'Choose a content backup inside this server.' }
$document = Get-Content -LiteralPath (Join-Path $BackupDirectory 'rollback.json') -Raw | ConvertFrom-Json
if ($document.schemaVersion -ne 1 -or $document.server -ine $ServerDirectory) { throw 'This backup belongs to another server.' }
Assert-CS15Stopped $ServerDirectory
foreach ($file in $document.files) {
    $target = Get-CS15ContentPath $ServerDirectory $file.path
    if (-not (Test-Path -LiteralPath $target -PathType Leaf) -or (Get-FileHash -LiteralPath $target).Hash -ine $file.installedSha256) { throw ('A file changed after this update; restore was stopped before changing files: ' + $file.path) }
    if ($file.existed -and -not (Test-Path -LiteralPath (Get-CS15ContentPath $BackupDirectory ('files/' + $file.path)) -PathType Leaf)) { throw 'A backup file is missing.' }
}
if ($PSCmdlet.ShouldProcess($ServerDirectory,'Restore the content backup')) {
    foreach ($file in $document.files) {
        $target = Get-CS15ContentPath $ServerDirectory $file.path
        if ($file.existed) { [IO.File]::Copy((Get-CS15ContentPath $BackupDirectory ('files/' + $file.path)),$target,$true) }
        else { Remove-Item -LiteralPath $target }
    }
    Write-Host 'Content backup restored. Original server configuration and ranking were not part of the update.'
}
