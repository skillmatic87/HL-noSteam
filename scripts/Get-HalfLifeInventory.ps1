[CmdletBinding()]
param(
    [string]$GameRoot
)

$ErrorActionPreference = 'Stop'
if ([string]::IsNullOrWhiteSpace($GameRoot)) {
    $GameRoot = Split-Path -Parent $PSScriptRoot
}
$resolvedRoot = (Resolve-Path -LiteralPath $GameRoot).Path

$files = foreach ($relativePath in @('hl.exe', 'hlds.exe', 'hw.dll', 'sw.dll', 'valve\dlls\hl.dll')) {
    $filePath = Join-Path $resolvedRoot $relativePath
    if (Test-Path -LiteralPath $filePath -PathType Leaf) {
        $file = Get-Item -LiteralPath $filePath
        [pscustomobject]@{
            File = $relativePath
            Bytes = $file.Length
            FileVersion = $file.VersionInfo.FileVersion
            ProductVersion = $file.VersionInfo.ProductVersion
            SHA256 = (Get-FileHash -LiteralPath $filePath -Algorithm SHA256).Hash
        }
    }
}

$readmePath = Join-Path $resolvedRoot 'readme.txt'
$readmeHeader = if (Test-Path -LiteralPath $readmePath -PathType Leaf) {
    @(Get-Content -LiteralPath $readmePath -TotalCount 5 | ForEach-Object { $_.ToString() })
} else { @() }

[pscustomobject]@{
    Files = @($files)
    ReadmeHeader = @($readmeHeader)
    HasCounterStrikeDirectory = (Test-Path -LiteralPath (Join-Path $resolvedRoot 'cstrike') -PathType Container)
    HasHalfLifeServerConfig = (Test-Path -LiteralPath (Join-Path $resolvedRoot 'valve\server.cfg') -PathType Leaf)
    RuntimeBuildVerified = $false
} | ConvertTo-Json -Depth 4
