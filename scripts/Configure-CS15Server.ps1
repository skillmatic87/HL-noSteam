[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$ServerDirectory,
    [string]$SettingsPath,
    [string]$BindAddress
)

$ErrorActionPreference = 'Stop'
$ServerDirectory = (Resolve-Path -LiteralPath $ServerDirectory).Path
$game = Join-Path $ServerDirectory 'cstrike'
if (-not (Test-Path -LiteralPath (Join-Path $game 'addons\statsme\dlls\sm_cstrike_mm.dll'))) { throw 'The CS 1.5 installation is incomplete.' }
if (Test-Path -LiteralPath (Join-Path $game 'server.cfg')) { throw 'Configuration already exists. Back it up and move it aside before reconfiguring.' }
$BindAddress = & (Join-Path $PSScriptRoot 'Get-CS15LANAddress.ps1') -BindAddress $BindAddress

if ($SettingsPath) {
    $settings = Get-Content -LiteralPath $SettingsPath -Raw | ConvertFrom-Json
} else {
    Write-Host 'Choose the server rules. No unanswered project preference is filled in automatically.'
    Write-Host 'Ranking is stored by player name on this LAN server. Reusing a name reuses its ranking.'
    $readInput = Join-Path $PSScriptRoot 'Read-CS15SetupInput.ps1'
    $settings = [pscustomobject]@{
        ServerName = & $readInput -Prompt 'Server name' -Kind Name
        MapMinutes = & $readInput -Prompt 'Map time limit in minutes' -Kind Integer -Minimum 6 -Maximum 180
        FriendlyFire = & $readInput -Prompt 'Enable Friendly Fire?' -Kind YesNo
        BotTarget = & $readInput -Prompt 'Fill with bots up to this total player count (0 disables bots)' -Kind Integer -Maximum 32
        BotDifficulty = & $readInput -Prompt 'Bot difficulty: 0 new, 1 easy, 2 medium, 3 hard, 4 expert' -Kind Integer -Maximum 4
        SoundCooldown = & $readInput -Prompt 'Minimum seconds between chat sounds' -Kind Integer -Maximum 300
        SoundQuota = & $readInput -Prompt 'Chat sound triggers per player per map' -Kind Integer -Minimum 1 -Maximum 1000
        RankBots = & $readInput -Prompt 'Include bots in the ranking?' -Kind YesNo
        RankScore = & $readInput -Prompt 'Ranking score' -Kind RankScore
        AdminName = & $readInput -Prompt 'Administrator player name (exact spelling)' -Kind Name
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
$launcher = @'
@echo off
cd /d "%~dp0"
hlds.exe -console -game cstrike -nomaster -insecure -noipx -port 27015 +ip __LAN_ADDRESS__ +sv_lan 1 +maxplayers 32 +map de_dust2
'@
$launcher.Replace('__LAN_ADDRESS__',$BindAddress) | Set-Content -LiteralPath (Join-Path $ServerDirectory 'Start-CS15.cmd') -Encoding ascii
Write-Host ('LAN address: '+$BindAddress+':27015. Update +ip in Start-CS15.cmd if this PC changes address.')
Write-Host 'Configuration complete. Your unique administrator credentials are in ADMIN.local.txt.'
Write-Host 'Start the server with Start-CS15.cmd. No firewall rule has been created.'
