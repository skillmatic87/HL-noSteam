[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$ServerDirectory,
    [string]$SettingsPath
)

$ErrorActionPreference = 'Stop'
$ServerDirectory = (Resolve-Path -LiteralPath $ServerDirectory).Path
$game = Join-Path $ServerDirectory 'cstrike'
if (-not (Test-Path -LiteralPath (Join-Path $game 'addons\statsme\dlls\sm_cstrike_mm.dll'))) { throw 'The CS 1.5 installation is incomplete.' }
if (Test-Path -LiteralPath (Join-Path $game 'server.cfg')) { throw 'Configuration already exists. Back it up and move it aside before reconfiguring.' }

if ($SettingsPath) {
    $settings = Get-Content -LiteralPath $SettingsPath -Raw | ConvertFrom-Json
} else {
    Write-Host 'Choose the server rules. No unanswered project preference is filled in automatically.'
    Write-Host 'Ranking is stored by player name on this LAN server. Reusing a name reuses its ranking.'
    $settings = [pscustomobject]@{
        ServerName = Read-Host 'Server name'
        MapMinutes = Read-Host 'Map time limit in minutes (6-180)'
        FriendlyFire = Read-Host 'Friendly Fire: 0 = off, 1 = on'
        BotTarget = Read-Host 'Fill with bots up to this total player count (0-32; 0 = no bots)'
        BotDifficulty = Read-Host 'Bot difficulty (0 = new, 1 = easy, 2 = medium, 3 = hard, 4 = expert)'
        SoundCooldown = Read-Host 'Minimum seconds between chat sounds (0-300)'
        SoundQuota = Read-Host 'Chat sound triggers per player per map (1-1000)'
        RankBots = Read-Host 'Include bots in the ranking: 0 = no, 1 = yes'
        RankScore = Read-Host 'Ranking score: KillsMinusDeaths or Kills'
        AdminName = Read-Host 'Administrator player name (exact spelling)'
    }
}

foreach ($field in @('ServerName','AdminName')) {
    $value = [string]$settings.$field
    if ([string]::IsNullOrWhiteSpace($value) -or $value.Length -gt 31 -or $value -match '[^\x20-\x7e]|[";\\]') { throw ('Use 1-31 printable ASCII characters without quotes, semicolons or backslashes for ' + $field) }
}
$ranges = @{MapMinutes=@(6,180);FriendlyFire=@(0,1);BotTarget=@(0,32);BotDifficulty=@(0,4);SoundCooldown=@(0,300);SoundQuota=@(1,1000);RankBots=@(0,1)}
foreach ($field in $ranges.Keys) {
    $value = [string]$settings.$field
    if ($value -notmatch '^\d+$' -or [long]$value -lt $ranges[$field][0] -or [long]$value -gt $ranges[$field][1]) { throw ('Invalid setting: ' + $field) }
}
if ($settings.RankScore -cnotin @('KillsMinusDeaths','Kills')) { throw 'RankScore must be KillsMinusDeaths or Kills.' }
$adminPassword = [Guid]::NewGuid().ToString('N')
$rconPassword = [Guid]::NewGuid().ToString('N')
$settings | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $ServerDirectory 'settings.local.json') -Encoding ascii
$serverConfig = @(
    '// Local operator configuration. Never publish this file.',
    ('hostname "' + $settings.ServerName + '"'), 'sv_lan 1', 'sv_allowdownload 1',
    ('rcon_password "' + $rconPassword + '"'),
    ('mp_timelimit ' + $settings.MapMinutes), ('mp_friendlyfire ' + $settings.FriendlyFire),
    'mp_maxrounds 0', 'mp_winlimit 0', 'log on'
)
$serverConfig | Set-Content -LiteralPath (Join-Path $game 'server.cfg') -Encoding ascii
$adminConfig = @(
    '; Name and password authentication. No default public administrator account.',
    ('"' + $settings.AdminName + '" "' + $adminPassword + '" "abcdefghijklmnopqrstu" "a"')
)
$adminConfig | Set-Content -LiteralPath (Join-Path $game 'addons\amxmodx\configs\users.ini') -Encoding ascii
@(
    'Private administrator instructions. Do not upload this file.',
    ('Player name: ' + $settings.AdminName),
    'Before connecting, enter this in your CS 1.5 client console:',
    ('setinfo _pw "' + $adminPassword + '"'),
    'After connecting: amxmodmenu',
    ('Server-console RCON password: ' + $rconPassword),
    'Keep this file private. Change credentials locally if it is disclosed.'
) | Set-Content -LiteralPath (Join-Path $ServerDirectory 'ADMIN.local.txt') -Encoding ascii

$statsmePath = Join-Path $game 'addons\statsme\statsme.cfg'
$statsme = [IO.File]::ReadAllText($statsmePath)
$score = if ($settings.RankScore -eq 'Kills') { '{rk.kills}' } else { '{{rk.kills}-{rk.deaths}}' }
foreach ($entry in @(@('sm_menupassword','""'),@('sm_storebyauth','0'),@('sm_resetrank','0'),@('sm_rankbots',[string]$settings.RankBots),@('sm_rankscore',('"' + $score + '"')))) {
    $statsme = [regex]::Replace($statsme, ('(?m)^' + $entry[0] + '\s+.*$'), ($entry[0] + ' ' + $entry[1]))
}
[IO.File]::WriteAllText($statsmePath,$statsme,[Text.Encoding]::ASCII)
$botPath = Join-Path $game 'addons\yapb\conf\yapb.cfg'
$bots = [IO.File]::ReadAllText($botPath)
foreach ($entry in @(@('yb_quota',[string]$settings.BotTarget),@('yb_quota_mode','fill'),@('yb_difficulty',[string]$settings.BotDifficulty))) {
    $bots = [regex]::Replace($bots, ('(?m)^' + $entry[0] + '\s+.*$'), ($entry[0] + ' "' + $entry[1] + '"'))
}
[IO.File]::WriteAllText($botPath,$bots,[Text.Encoding]::ASCII)
$soundConfig = @(
    ('SND_MAX; ' + $settings.SoundQuota), 'SND_MAX_DUR; 180.0',
    ('SND_WARN; ' + [Math]::Max(1,([int]$settings.SoundQuota - 3))), 'SND_JOIN;', 'SND_EXIT;',
    ('SND_DELAY; ' + $settings.SoundCooldown), 'SND_MODE; 15', 'SND_OBEY_DUR; 7',
    'EXACT_MATCH; 1', 'ADMINS_ONLY; 0', 'DISPLAY_KEYWORDS; 1', 'FREEZE_TIME_CON; 0'
)
$soundNames = @('dominating','doublekill','firstblood','godlike','headshot','humiliation','killingspree','monsterkill','multikill','perfect','prepare','rampage','ultrakill','unstoppable')
$soundConfig += $soundNames | ForEach-Object { $_ + '; sound/misc/' + $_ + '.wav' }
$soundConfig | Set-Content -LiteralPath (Join-Path $game 'addons\amxmodx\configs\SND-LIST.CFG') -Encoding ascii
@'
@echo off
cd /d "%~dp0"
hlds.exe -console -game cstrike -nomaster -insecure -noipx -port 27015 +sv_lan 1 +maxplayers 32 +map de_dust2
'@ | Set-Content -LiteralPath (Join-Path $ServerDirectory 'Start-CS15.cmd') -Encoding ascii
Write-Host 'Configuration complete. Your unique administrator credentials are in ADMIN.local.txt.'
Write-Host 'Start the server with Start-CS15.cmd. No firewall rule has been created.'
