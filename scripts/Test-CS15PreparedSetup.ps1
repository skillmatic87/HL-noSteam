[CmdletBinding()]
param([Parameter(Mandatory = $true)][string]$ServerDirectory)

$ErrorActionPreference = 'Stop'
# Resume configuration only when setup finished preparing files and has not
# written operator settings or credentials. Existing operator data is protected.
foreach ($path in @('Start-CS15.cmd','ADMIN.local.txt','settings.local.json','COMPONENTS.json','cstrike\server.cfg','cstrike\addons\amxmodx\configs\SND-LIST.CFG')) {
    if (Test-Path -LiteralPath (Join-Path $ServerDirectory $path)) { return $false }
}
foreach ($path in @('hlds.exe','SERVER-LICENSE.txt','_setup\upstream-server.cfg','cstrike\liblist.gam','cstrike\mapcycle.txt',
    'cstrike\addons\metamod\plugins.ini','cstrike\addons\metamod\dlls\metamod.dll',
    'cstrike\addons\amxmodx\dlls\amxmodx_mm.dll','cstrike\addons\amxmodx\plugins\mapmanager.amxx',
    'cstrike\addons\amxmodx\plugins\sank_sounds.amxx','cstrike\addons\amxmodx\configs\mapmanager.cfg',
    'cstrike\addons\statsme\dlls\sm_cstrike_mm.dll','cstrike\addons\yapb\bin\yapb.dll')) {
    if (-not (Test-Path -LiteralPath (Join-Path $ServerDirectory $path) -PathType Leaf)) { return $false }
}
foreach ($pair in @(
    @('cstrike\addons\amxmodx\configs\users.ini','_setup\amxx\addons\amxmodx\configs\users.ini'),
    @('cstrike\addons\statsme\statsme.cfg','_setup\statsme\addons\statsme\statsme.cfg'),
    @('cstrike\addons\yapb\conf\yapb.cfg','_setup\bots\addons\yapb\conf\yapb.cfg')
)) {
    $installed = Join-Path $ServerDirectory $pair[0]
    $original = Join-Path $ServerDirectory $pair[1]
    if (-not (Test-Path -LiteralPath $installed -PathType Leaf) -or -not (Test-Path -LiteralPath $original -PathType Leaf)) { return $false }
    if ((Get-FileHash -LiteralPath $installed).Hash -ne (Get-FileHash -LiteralPath $original).Hash) { return $false }
}
$maps = @(Get-ChildItem -LiteralPath (Join-Path $ServerDirectory 'cstrike\maps') -Filter '*.bsp' -ErrorAction SilentlyContinue)
if ($maps.Count -ne 26) { return $false }
foreach ($map in $maps) {
    if (-not (Test-Path -LiteralPath (Join-Path $ServerDirectory ('cstrike\addons\yapb\data\graph\' + $map.BaseName + '.graph')))) { return $false }
}
return $true
