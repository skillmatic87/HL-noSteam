[CmdletBinding()]
param(
    [ValidateSet('Auto','FHD','QHD','4K','Safe')][string]$Resolution = 'Auto',
    [switch]$Windowed,
    [switch]$ListModes,
    [switch]$Log
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$display = & (Join-Path $PSScriptRoot 'Get-CS15DisplayModes.ps1')
$profiles = [ordered]@{Auto=@($display.Width,$display.Height);FHD=@(1920,1080);QHD=@(2560,1440);'4K'=@(3840,2160);Safe=@(1024,768)}
if ($ListModes) {
    foreach ($name in $profiles.Keys) {
        $size=$profiles[$name]
        [pscustomobject]@{Profile=$name;Width=$size[0];Height=$size[1];Available=@($display.Modes | Where-Object { $_.Width -eq $size[0] -and $_.Height -eq $size[1] }).Count -gt 0}
    }
    return
}
$size=$profiles[$Resolution]
if (-not @($display.Modes | Where-Object { $_.Width -eq $size[0] -and $_.Height -eq $size[1] }).Count) {
    throw ('The primary display does not currently offer '+$size[0]+'x'+$size[1]+'. Use Auto, FHD, QHD or Safe; 4K requires a supported Windows display mode.')
}
$executable=Join-Path $root 'hl.exe'
if (-not (Test-Path -LiteralPath $executable -PathType Leaf) -or -not (Test-Path -LiteralPath (Join-Path $root 'hl_fov_fix.asi') -PathType Leaf)) { throw 'The Half-Life WON widescreen patch is not installed here.' }
foreach ($process in @(Get-CimInstance Win32_Process -Filter "Name = 'hl.exe'")) {
    if ($process.ExecutablePath -ieq $executable) { throw 'This Half-Life client is already running. Quit it before switching resolution or connecting with a launcher.' }
}
. (Join-Path $PSScriptRoot 'CS15Client.Common.ps1')
Set-CS15VideoSettings -Width $size[0] -Height $size[1] -Windowed ([bool]$Windowed)
$arguments=@('-console','-game','cstrike','-gl','-gldrv','Default','-32bpp','-noextracds','-nomaster','-noipx','-width',[string]$size[0],'-height',[string]$size[1])
if ($Windowed) { $arguments+='-window' } else { $arguments+='-full' }
if ($Log) { $arguments+='-condebug' }
Write-Host ('Starting CS 1.5 at '+$size[0]+'x'+$size[1]+' in OpenGL')
Start-Process -FilePath $executable -ArgumentList $arguments -WorkingDirectory $root -WindowStyle Normal
