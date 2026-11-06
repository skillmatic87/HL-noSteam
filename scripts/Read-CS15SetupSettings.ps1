[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$reader = Join-Path $PSScriptRoot 'Read-CS15SetupInput.ps1'
function Read-ConfirmedNumber {
    param([string]$Question,[int]$Suggested,[string]$CustomPrompt,[int]$Minimum,[int]$Maximum)
    if (& $reader -Prompt $Question -Kind YesNo) { return $Suggested }
    return & $reader -Prompt $CustomPrompt -Kind Integer -Minimum $Minimum -Maximum $Maximum
}
Write-Host 'Answer y or n. Names and custom values are entered when requested.'
Write-Host 'Ranking is stored by player name on this LAN server. Reusing a name reuses its ranking.'
$settings = [ordered]@{}
$settings.ServerName = & $reader -Prompt '1. Server name' -Kind ServerName
$settings.MapMinutes = Read-ConfirmedNumber '2. Use a 20-minute map time limit?' 20 'Map time limit in minutes' 6 180
$settings.FriendlyFire = & $reader -Prompt '3. Enable friendly fire?' -Kind YesNo
$settings.BotTarget = 0
$settings.BotDifficulty = 2
if (& $reader -Prompt '4. Enable bots?' -Kind YesNo) {
    $settings.BotTarget = Read-ConfirmedNumber '5. Use bots to fill the server up to 16 players?' 16 'Total players to fill with bots' 1 32
    $settings.BotDifficulty = Read-ConfirmedNumber '6. Use medium bot difficulty?' 2 'Bot difficulty: 0 novice, 1 easy, 2 medium, 3 hard, 4 expert' 0 4
}
$settings.SoundCooldown = Read-ConfirmedNumber '7. Use a 3-second cooldown between chat sounds?' 3 'Seconds between chat sounds' 0 300
$settings.SoundQuota = Read-ConfirmedNumber '8. Limit each player to 100 chat sounds per map?' 100 'Chat sounds per player per map' 1 1000
$settings.RankBots = & $reader -Prompt '9. Include bots in the ranking?' -Kind YesNo
$settings.RankScore = if (& $reader -Prompt '10. Rank players by kills minus deaths?' -Kind YesNo) { 'KillsMinusDeaths' } else { 'Kills' }
$settings.AdminName = & $reader -Prompt '11. Administrator player name' -Kind Name
[pscustomobject]$settings
