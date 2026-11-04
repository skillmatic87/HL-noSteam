[CmdletBinding(SupportsShouldProcess = $true)]
param([string]$ServerDirectory)
$ErrorActionPreference = 'Stop'
if (-not $ServerDirectory) {
    $ServerDirectory = Join-Path (Split-Path -Parent $PSScriptRoot) 'CS15Server'
}
$launcher = Join-Path $ServerDirectory 'Start-CS15.cmd'
if (-not (Test-Path -LiteralPath $launcher -PathType Leaf)) {
    throw 'Installed server not found. Run Setup.cmd first, or use Start-Server.cmd -ServerDirectory "D:\YourServer".'
}
$ServerDirectory = (Resolve-Path -LiteralPath $ServerDirectory).Path
if (Test-Path -LiteralPath (Join-Path $ServerDirectory '.install-incomplete')) {
    throw 'The server installation is incomplete. Complete setup before starting it.'
}
if (-not (Test-Path -LiteralPath (Join-Path $ServerDirectory 'hlds.exe') -PathType Leaf)) {
    throw 'hlds.exe is missing from the selected server folder. Check the installation.'
}
if ($PSCmdlet.ShouldProcess($ServerDirectory, 'Start the installed CS 1.5 server')) {
    Push-Location -LiteralPath $ServerDirectory
    try {
        & (Join-Path $ServerDirectory 'Start-CS15.cmd')
        $result = $LASTEXITCODE
    } finally {
        Pop-Location
    }
    exit $result
}
