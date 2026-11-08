[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$researchRoot = Join-Path $projectRoot 'downloads\research'
$serverRoot = Join-Path $projectRoot 's'
$gameRoot = Join-Path $serverRoot 'cstrike'

# The CS-specific StatsMe 2.7 build uses a fixed mod name rather than an engine path.

if (-not (Test-Path -LiteralPath (Join-Path $serverRoot 'hlds.exe'))) {
    throw 'The isolated baseline server must be prepared first.'
}

# This script modifies only the disposable integration-test server.
$pidFile = Join-Path $serverRoot 'test-process.pid'
if (Test-Path -LiteralPath $pidFile) {
    $testProcessId = [int](Get-Content -LiteralPath $pidFile -Raw)
    $testProcess = Get-Process -Id $testProcessId -ErrorAction SilentlyContinue
    if ($testProcess) {
        if ($testProcess.Path -ne (Join-Path $serverRoot 'hlds.exe')) {
            throw 'The saved process ID belongs to a different executable.'
        }
        Stop-Process -Id $testProcessId
        $testProcess.WaitForExit(5000) | Out-Null
    }
}

& tar -xf (Join-Path $researchRoot 'metamod-p-v1.21p109-win32.tar.xz') -C $gameRoot
if ($LASTEXITCODE -ne 0) { throw 'Metamod extraction failed.' }
Copy-Item -LiteralPath (Join-Path $researchRoot 'amxx181\addons') -Destination $gameRoot -Recurse -Force
Expand-Archive -LiteralPath (Join-Path $researchRoot 'statsme-2.7-cstrike.zip') -DestinationPath $gameRoot -Force
Copy-Item -LiteralPath (Join-Path $researchRoot 'yapb\addons') -Destination $gameRoot -Recurse -Force

$amxxRoot = Join-Path $gameRoot 'addons\amxmodx'
$mapManagerRoot = Join-Path $researchRoot 'mapmanager\MapManager-master'
$mapManagerSource = [System.IO.File]::ReadAllText((Join-Path $mapManagerRoot 'mapmanager.sma'))
$originalRoundEvent = 'register_event("HLTV", "Event_NewRound", "a", "1=0", "2=0");'
if (-not $mapManagerSource.Contains($originalRoundEvent)) { throw 'Unexpected upstream Map Manager source.' }
# CS 1.5 exposes Round_Start in its game log instead of the CS 1.6 HLTV event.
$mapManagerSource = $mapManagerSource.Replace($originalRoundEvent, 'register_logevent("Event_NewRound", 2, "0=World triggered", "1=Round_Start");')
$mapManagerSource = $mapManagerSource.Replace('#define VERSION "2.5.61"', '#define VERSION "2.5.61-cs15"')
$adaptedMapSource = Join-Path $mapManagerRoot 'mapmanager_cs15.sma'
[System.IO.File]::WriteAllText($adaptedMapSource, $mapManagerSource, (New-Object System.Text.UTF8Encoding($false)))
$compilerRoot = Join-Path $researchRoot 'amxx181\addons\amxmodx\scripting'
$adaptedMapBinary = Join-Path $mapManagerRoot 'mapmanager_cs15.amxx'
if (Test-Path -LiteralPath $adaptedMapBinary) {
    Remove-Item -LiteralPath $adaptedMapBinary
}
$compilerOutput = @(& (Join-Path $compilerRoot 'amxxpc.exe') $adaptedMapSource ('-i' + (Join-Path $compilerRoot 'include')) ('-i' + (Join-Path $mapManagerRoot 'include')) ('-o' + $adaptedMapBinary))
$compilerOutput | Write-Output
if ($LASTEXITCODE -ne 0 -or ($compilerOutput -match 'error [0-9]|Compilation aborted|compile failed') -or -not (Test-Path -LiteralPath $adaptedMapBinary)) { throw 'Map Manager compatibility build failed.' }
Copy-Item -LiteralPath $adaptedMapBinary -Destination (Join-Path $amxxRoot 'plugins\mapmanager.amxx') -Force
$sankSource = Join-Path $researchRoot 'sank\HL1_SankSounds-master\sank_sounds.sma'
$sankBinary = Join-Path $researchRoot 'sank\sank_sounds.amxx'
if (Test-Path -LiteralPath $sankBinary) { Remove-Item -LiteralPath $sankBinary }
$sankCompilerOutput = @(& (Join-Path $compilerRoot 'amxxpc.exe') $sankSource ('-i' + (Join-Path $compilerRoot 'include')) ('-o' + $sankBinary))
$sankCompilerOutput | Write-Output
if ($LASTEXITCODE -ne 0 -or ($sankCompilerOutput -match 'error [0-9]|Compilation aborted|compile failed') -or -not (Test-Path -LiteralPath $sankBinary)) { throw 'Sank Sounds build failed.' }
Copy-Item -LiteralPath $sankBinary -Destination (Join-Path $amxxRoot 'plugins') -Force
Copy-Item -LiteralPath $adaptedMapSource -Destination (Join-Path $amxxRoot 'scripting') -Force
Copy-Item -LiteralPath (Join-Path $researchRoot 'sank\HL1_SankSounds-master\sank_sounds.sma') -Destination (Join-Path $amxxRoot 'scripting') -Force

$englishDictionary = New-Object System.Collections.Generic.List[string]
$readingEnglish = $false
foreach ($dictionaryLine in Get-Content -LiteralPath (Join-Path $mapManagerRoot 'mapmanager.txt')) {
    if ($dictionaryLine -match '^\[([^]]+)\]') {
        if ($readingEnglish) { break }
        $readingEnglish = $Matches[1] -eq 'en'
    }
    if ($readingEnglish) { $englishDictionary.Add($dictionaryLine) }
}
$englishDictionary | Set-Content -LiteralPath (Join-Path $amxxRoot 'data\lang\mapmanager.txt') -Encoding ascii
$mapManagerConfig = [System.IO.File]::ReadAllText((Join-Path $mapManagerRoot 'mapmanager.cfg'))
$mapManagerConfig = $mapManagerConfig.Replace('mapm_start_vote_before_end 2', 'mapm_start_vote_before_end 5')
Set-Content -LiteralPath (Join-Path $amxxRoot 'configs\mapmanager.cfg') -Value $mapManagerConfig -Encoding ascii

$maps = @(Get-ChildItem -LiteralPath (Join-Path $gameRoot 'maps') -Filter '*.bsp' | Sort-Object Name | ForEach-Object { $_.BaseName })
$maps | Set-Content -LiteralPath (Join-Path $amxxRoot 'configs\maps.ini') -Encoding ascii

@'
; One map-vote system; StatsMe provides statistics separately.
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
'@ | Set-Content -LiteralPath (Join-Path $amxxRoot 'configs\plugins.ini') -Encoding ascii

@'
win32 addons/amxmodx/dlls/amxmodx_mm.dll
win32 addons/statsme/dlls/sm_cstrike_mm.dll
win32 addons/yapb/bin/yapb.dll
'@ | Set-Content -LiteralPath (Join-Path $gameRoot 'addons\metamod\plugins.ini') -Encoding ascii

# No administrator identity or password is embedded in the public script.
'; Configure test administrator credentials locally.' | Set-Content -LiteralPath (Join-Path $amxxRoot 'configs\users.ini') -Encoding ascii
Add-Content -LiteralPath (Join-Path $amxxRoot 'configs\amxx.cfg') -Encoding ascii -Value "`namx_language en`namx_client_languages 0"

$liblistPath = Join-Path $gameRoot 'liblist.gam'
$liblist = [System.IO.File]::ReadAllText($liblistPath)
$liblist = [regex]::Replace($liblist, '(?m)^gamedll\s+"[^"]+"', 'gamedll "addons/metamod/dlls/metamod.dll"')
Set-Content -LiteralPath $liblistPath -Value $liblist -Encoding ascii

$statsmePath = Join-Path $gameRoot 'addons\statsme\statsme.cfg'
$statsme = [System.IO.File]::ReadAllText($statsmePath)
$statsme = [regex]::Replace($statsme, '(?m)^sm_menupassword\s+.*$', 'sm_menupassword ""')
$statsme = [regex]::Replace($statsme, '(?m)^sm_storebyauth\s+.*$', 'sm_storebyauth 0')
$statsme = [regex]::Replace($statsme, '(?m)^sm_resetrank\s+.*$', 'sm_resetrank 0')
$statsme = [regex]::Replace($statsme, '(?m)^sm_rankhead\s+.*$', 'sm_rankhead "#  nick                     kills/deaths   hits/shots/hs.   eff.%%   acc.%%"')
$statsme = [regex]::Replace($statsme, '(?m)^sm_rankbody\s+.*$', 'sm_rankbody "{rk.id}.  {rk.name}{rk.txt} {rk.kills}/{rk.deaths}   {rk.hits}/{rk.shots}/{rk.hs}   {rk.eff}    {rk.acc}"')
Set-Content -LiteralPath $statsmePath -Value $statsme -Encoding ascii

# Include only the existing sound directory, preserving original map resources.
$soundExtractRoot = Join-Path $researchRoot 'statsme-sounds'
Expand-Archive -LiteralPath (Join-Path $researchRoot 'statsme-soundpack.zip') -DestinationPath $soundExtractRoot -Force
Copy-Item -LiteralPath (Join-Path $soundExtractRoot 'sound') -Destination $gameRoot -Recurse -Force
$soundFiles = @(Get-ChildItem -LiteralPath (Join-Path $gameRoot 'sound\misc') -Filter '*.wav' | Where-Object { $_.BaseName -in @('dominating','doublekill','firstblood','godlike','headshot','humiliation','killingspree','monsterkill','multikill','perfect','prepare','rampage','ultrakill','unstoppable') } | Sort-Object Name)
$soundConfig = @('SND_MAX; 20','SND_MAX_DUR; 180.0','SND_WARN; 17','SND_JOIN;','SND_EXIT;','SND_DELAY; 0.0','SND_MODE; 15','SND_OBEY_DUR; 7','EXACT_MATCH; 1','ADMINS_ONLY; 0','DISPLAY_KEYWORDS; 1','FREEZE_TIME_CON; 0','# Existing classic sound pack; integration-test settings, not approved final quotas.')
$soundConfig += $soundFiles | ForEach-Object { $_.BaseName + '; sound/misc/' + $_.Name }
$soundConfig | Set-Content -LiteralPath (Join-Path $amxxRoot 'configs\SND-LIST.CFG') -Encoding ascii

$botConfigPath = Join-Path $gameRoot 'addons\yapb\conf\yapb.cfg'
$botConfig = [System.IO.File]::ReadAllText($botConfigPath)
$botConfig = [regex]::Replace($botConfig, '(?m)^yb_quota\s+.*$', 'yb_quota "2" // Integration test only.')
Set-Content -LiteralPath $botConfigPath -Value $botConfig -Encoding ascii

$testPassword = [Guid]::NewGuid().ToString('N').Substring(0,20)
$testPassword | Set-Content -LiteralPath (Join-Path $serverRoot 'test-rcon.secret') -Encoding ascii
@(
    '// Disposable integration-test control; not a production server policy.',
    'echo Integration control loaded',
    ('rcon_password "' + $testPassword + '"'),
    'version','status','meta list','amxx plugins','amxx modules',
    'mapm_start_vote_before_end','sanksounds_version','statsme_version','yb version'
) | Set-Content -LiteralPath (Join-Path $gameRoot 'integration.cfg') -Encoding ascii

[pscustomobject]@{ Server = 's'; OriginalMaps = $maps.Count; ChatSounds = $soundFiles.Count; VoteLeadMinutes = 5; TestBots = 2; RuntimeVerified = $false }
