[CmdletBinding()]
param(
    [string]$Destination,
    [string]$CacheDirectory,
    [string]$SettingsPath,
    # Kept for older command lines; setup no longer prompts for license consent.
    [switch]$AcceptServerLicense
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
if (-not $Destination) { $Destination = Join-Path $projectRoot 'CS15Server' }
$Destination = [IO.Path]::GetFullPath($Destination)
$incompleteMarker = Join-Path $Destination '.install-incomplete'
$markerText = 'Setup is incomplete. Do not start this installation.'
$resumeConfiguration = $false
if (Test-Path -LiteralPath $Destination) {
    $existing = Get-Item -LiteralPath $Destination
    $expectedFiles = @('_setup','.install-incomplete','SERVER-LICENSE.txt')
    $unexpectedFiles = @(Get-ChildItem -LiteralPath $Destination -Force | Where-Object { $_.Name -notin $expectedFiles })
    if (-not $existing.PSIsContainer -or ($existing.Attributes -band [IO.FileAttributes]::ReparsePoint) -or
        -not (Test-Path -LiteralPath $incompleteMarker -PathType Leaf) -or
        (Get-Content -LiteralPath $incompleteMarker -Raw).Trim() -ne $markerText) {
        throw 'The destination already contains an installation or other files. Choose a new destination; existing installations are not overwritten.'
    }
    if (@(Get-ChildItem -LiteralPath $Destination -Recurse -Force | Where-Object { $_.Attributes -band [IO.FileAttributes]::ReparsePoint }).Count) {
        throw 'Setup cannot resume a directory containing links or junctions. Choose a new destination.'
    }
    if ($unexpectedFiles.Count) {
        $resumeConfiguration = & (Join-Path $PSScriptRoot 'Test-CS15PreparedSetup.ps1') -ServerDirectory $Destination
        if (-not $resumeConfiguration) { throw 'This directory contains a partial installation or operator settings that cannot be overwritten. Choose a new destination; existing files have been preserved.' }
        Write-Host 'Server files are already prepared. Continuing with server configuration.'
    } else {
        Write-Host 'Resuming setup preparation. Downloaded archives will be reused after verification.'
    }
}
if (-not (Get-Command curl.exe -ErrorAction SilentlyContinue) -or -not (Get-Command tar.exe -ErrorAction SilentlyContinue)) { throw 'Windows curl.exe and tar.exe are required.' }
if (-not $CacheDirectory) { $CacheDirectory = Join-Path $projectRoot 'downloads\packages' }
$components = & (Join-Path $PSScriptRoot 'Get-CS15Components.ps1') -CacheDirectory $CacheDirectory
New-Item -ItemType Directory -Path $Destination -Force | Out-Null
$markerText | Set-Content -LiteralPath $incompleteMarker -Encoding ascii
$work = Join-Path $Destination '_setup'
New-Item -ItemType Directory -Path $work -Force | Out-Null
if (-not $resumeConfiguration) {
foreach ($id in @('unpacker','cs15','amxx','statsme','statsmeSource','sank','mapmanager','bots','sounds')) {
    Write-Host ('Extracting ' + $id)
    Expand-Archive -LiteralPath $components[$id] -DestinationPath (Join-Path $work $id) -Force
}
$wise = Join-Path $work 'unpacker\WiseUnpacker.exe'
# A fresh extraction directory avoids modifying an earlier extraction on retry.
$hldsOutput = Join-Path $work ('server-' + [Guid]::NewGuid().ToString('N'))
$extractLog = Join-Path $work 'server-extraction.txt'
& $wise -x -o $hldsOutput $components.server *> $extractLog
if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath (Join-Path $hldsOutput 'MAINDIR\hlds.exe'))) { throw 'The original server installer could not be extracted. See _setup/server-extraction.txt.' }
$eula = Join-Path $hldsOutput 'TEMP\EULAFILE'
if (-not (Test-Path -LiteralPath $eula)) { throw 'The server license is missing.' }
Copy-Item -LiteralPath $eula -Destination (Join-Path $Destination 'SERVER-LICENSE.txt')
Copy-Item -Path (Join-Path $hldsOutput 'MAINDIR\*') -Destination $Destination -Recurse
$csRoot = @(Get-ChildItem -LiteralPath (Join-Path $work 'cs15') -Directory)
if ($csRoot.Count -ne 1) { throw 'Unexpected CS archive layout.' }
Copy-Item -LiteralPath (Join-Path $csRoot[0].FullName 'cstrike') -Destination $Destination -Recurse
$game = Join-Path $Destination 'cstrike'
foreach ($id in @('amxx','statsme','bots')) { Copy-Item -LiteralPath (Join-Path $work ($id + '\addons')) -Destination $game -Recurse -Force }
& tar.exe -xf $components.metamod -C $game
if ($LASTEXITCODE -ne 0) { throw 'Metamod extraction failed.' }
Copy-Item -LiteralPath (Join-Path $work 'sounds\sound') -Destination $game -Recurse -Force
Copy-Item -LiteralPath $components.graphTundra,$components.graphVegas -Destination (Join-Path $game 'addons\yapb\data\graph') -Force
foreach ($id in @('graphLicense','graphCredits','graphReadme')) { Copy-Item -LiteralPath $components[$id] -Destination $work }
$amxx = Join-Path $game 'addons\amxmodx'
$mapRoot = @(Get-ChildItem -LiteralPath (Join-Path $work 'mapmanager') -Directory)[0].FullName
$sankRoot = @(Get-ChildItem -LiteralPath (Join-Path $work 'sank') -Directory)[0].FullName
$mapSource = [IO.File]::ReadAllText((Join-Path $mapRoot 'mapmanager.sma'))
$roundEvent = 'register_event("HLTV", "Event_NewRound", "a", "1=0", "2=0");'
if (-not $mapSource.Contains($roundEvent)) { throw 'Unexpected Map Manager source.' }
$mapSource = $mapSource.Replace($roundEvent,'register_logevent("Event_NewRound", 2, "0=World triggered", "1=Round_Start");').Replace('#define VERSION "2.5.61"','#define VERSION "2.5.61-cs15"')
$adaptedSource = Join-Path $mapRoot 'mapmanager_cs15.sma'
[IO.File]::WriteAllText($adaptedSource,$mapSource,(New-Object Text.UTF8Encoding($false)))
$compiler = Join-Path $amxx 'scripting\amxxpc.exe'
foreach ($plugin in @(@{Source=$adaptedSource;Name='mapmanager';ExtraInclude=(Join-Path $mapRoot 'include')},@{Source=(Join-Path $sankRoot 'sank_sounds.sma');Name='sank_sounds';ExtraInclude=(Join-Path $mapRoot 'include')})) {
    $binary = Join-Path $amxx ('plugins\' + $plugin.Name + '.amxx')
    $diagnostics = @(& $compiler $plugin.Source ('-i' + (Join-Path $amxx 'scripting\include')) ('-i' + $plugin.ExtraInclude) ('-o' + $binary))
    if ($LASTEXITCODE -ne 0 -or ($diagnostics -match 'error [0-9]|Compilation aborted|compile failed') -or -not (Test-Path -LiteralPath $binary)) { $diagnostics | Out-Host; throw ('Plugin compilation failed: ' + $plugin.Name) }
    Copy-Item -LiteralPath $plugin.Source -Destination (Join-Path $amxx 'scripting')
}
$english = New-Object Collections.Generic.List[string]
$inEnglish = $false
foreach ($line in Get-Content -LiteralPath (Join-Path $mapRoot 'mapmanager.txt')) {
    if ($line -match '^\[([^]]+)\]') { if ($inEnglish) { break }; $inEnglish = $Matches[1] -eq 'en' }
    if ($inEnglish) { $english.Add($line) }
}
if ($english.Count -eq 0) { throw 'The English Map Manager dictionary is missing.' }
$english | Set-Content -LiteralPath (Join-Path $amxx 'data\lang\mapmanager.txt') -Encoding ascii
$mapConfig = [IO.File]::ReadAllText((Join-Path $mapRoot 'mapmanager.cfg')).Replace('mapm_start_vote_before_end 2','mapm_start_vote_before_end 5')
[IO.File]::WriteAllText((Join-Path $amxx 'configs\mapmanager.cfg'),$mapConfig,[Text.Encoding]::ASCII)
@'
admin.amxx
admincmd.amxx
adminhelp.amxx
multilingual.amxx
menufront.amxx
cmdmenu.amxx
plmenu.amxx
mapsmenu.amxx
pluginmenu.amxx
adminchat.amxx
antiflood.amxx
adminvote.amxx
pausecfg.amxx
mapmanager.amxx
sank_sounds.amxx
'@ | Set-Content -LiteralPath (Join-Path $amxx 'configs\plugins.ini') -Encoding ascii
@'
win32 addons/amxmodx/dlls/amxmodx_mm.dll
win32 addons/statsme/dlls/sm_cstrike_mm.dll
win32 addons/yapb/bin/yapb.dll
'@ | Set-Content -LiteralPath (Join-Path $game 'addons\metamod\plugins.ini') -Encoding ascii
$amxxConfig = [IO.File]::ReadAllText((Join-Path $amxx 'configs\amxx.cfg'))
$amxxConfig = [regex]::Replace($amxxConfig,'(?m)^amx_client_languages\s+.*$','amx_client_languages 0')
[IO.File]::WriteAllText((Join-Path $amxx 'configs\amxx.cfg'),($amxxConfig + "`namx_language en`n"),[Text.Encoding]::ASCII)
$liblist = [IO.File]::ReadAllText((Join-Path $game 'liblist.gam'))
$liblist = [regex]::Replace($liblist,'(?m)^gamedll\s+"[^"]+"','gamedll "addons/metamod/dlls/metamod.dll"')
[IO.File]::WriteAllText((Join-Path $game 'liblist.gam'),$liblist,[Text.Encoding]::ASCII)
$maps = @(Get-ChildItem -LiteralPath (Join-Path $game 'maps') -Filter '*.bsp' | Sort-Object Name | ForEach-Object BaseName)
if ($maps.Count -ne 26) { throw 'The expected 26 original maps are missing.' }
foreach ($map in $maps) {
    if (-not (Test-Path -LiteralPath (Join-Path $game ('addons\yapb\data\graph\' + $map + '.graph')))) { throw ('Bot navigation data is missing: ' + $map) }
}
$maps | Set-Content -LiteralPath (Join-Path $amxx 'configs\maps.ini') -Encoding ascii
$maps | Set-Content -LiteralPath (Join-Path $game 'mapcycle.txt') -Encoding ascii
# The archived client configuration is replaced only in this new installation.
$originalConfig = Join-Path $game 'server.cfg'
if (Test-Path -LiteralPath $originalConfig) { Move-Item -LiteralPath $originalConfig -Destination (Join-Path $work 'upstream-server.cfg') }
}
& (Join-Path $PSScriptRoot 'Configure-CS15Server.ps1') -ServerDirectory $Destination -SettingsPath $SettingsPath
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'components.json') -Destination (Join-Path $Destination 'COMPONENTS.json')
Copy-Item -LiteralPath $components.server -Destination (Join-Path $work 'hlserver4110.exe')
Remove-Item -LiteralPath $incompleteMarker
Write-Host 'Base server configuration is complete. Installing additional content; if this step fails, rerun Update-CS15Content.ps1 for this server.'
& (Join-Path $PSScriptRoot 'Update-CS15Content.ps1') -ServerDirectory $Destination
Write-Host ('Installation finished: ' + $Destination)
Write-Host 'Original installer, source archives/extractions and notices are retained in _setup and the download cache.'
