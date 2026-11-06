$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'CS15Setup.Common.ps1')
$script:answers = New-Object Collections.Queue
$script:prompts = New-Object Collections.Generic.List[string]
$queue = $script:answers
$promptLog = $script:prompts
$readResponse = {
    param([string]$Prompt,[switch]$AsSecureString)
    $promptLog.Add($Prompt)
    if (-not $queue.Count) { throw 'Unexpected wizard prompt.' }
    $value = $queue.Dequeue()
    if ($AsSecureString) {
        $secure = New-Object Security.SecureString
        foreach ($character in $value.ToCharArray()) { $secure.AppendChar($character) }
        return $secure
    }
    return $value
}.GetNewClosure()
Set-Item -Path Function:Read-Host -Value $readResponse
function Set-Answers {
    param([string[]]$Values)
    $script:answers.Clear();$script:prompts.Clear()
    foreach ($value in $Values) { $script:answers.Enqueue($value) }
}
function Assert-Equal {
    param($Actual,$Expected,[string]$Message)
    if ($Actual -cne $Expected) { throw $Message }
}
$recommended = @('LAN fixture','j','n','y','ja','YES','y','j','n','y','TestAdmin')
Set-Answers $recommended
$settings = & (Join-Path $PSScriptRoot 'Read-CS15SetupSettings.ps1')
foreach ($pair in @(@('MapMinutes',20),@('FriendlyFire',0),@('BotTarget',16),@('BotDifficulty',2),@('SoundCooldown',3),@('SoundQuota',100),@('RankBots',0),@('RankScore','KillsMinusDeaths'))) {
    Assert-Equal $settings.($pair[0]) $pair[1] 'A confirmed setting was not applied.'
}
Assert-Equal $script:answers.Count 0 'Unused wizard answers.'
Assert-Equal $script:prompts.Count 11 'Unexpected recommended question count.'
Set-Answers @('LAN fixture','y','n','n','y','y','n','n','TestAdmin')
$disabled = & (Join-Path $PSScriptRoot 'Read-CS15SetupSettings.ps1')
Assert-Equal $disabled.BotTarget 0 'Bots were not disabled.'
Assert-Equal $disabled.BotDifficulty 2 'Inactive bot difficulty must remain medium.'
Assert-Equal $disabled.RankScore 'Kills' 'The alternative ranking was not applied.'
if ($script:prompts -match '^[56]\.') { throw 'Disabled bots still asked follow-up questions.' }
Assert-Equal $script:answers.Count 0 'Unused disabled-bot answers.'
Set-Answers @('Custom fixture','n','5','180','j','j','n','0','32','n','4','n','0','n','1000','j','n','TestAdmin')
$custom = & (Join-Path $PSScriptRoot 'Read-CS15SetupSettings.ps1')
foreach ($pair in @(@('MapMinutes',180),@('BotTarget',32),@('BotDifficulty',4),@('SoundCooldown',0),@('SoundQuota',1000))) {
    Assert-Equal $custom.($pair[0]) $pair[1] 'Custom setting or boundary rejected.'
}
Assert-Equal $script:answers.Count 0 'Unused custom answers.'
Set-Answers @('','bad space',('x' * 32),'match$&','MATCH$&','match$&','match$&')
$password = Read-CS15SetupPassword 'Password fixture'
Assert-Equal $password 'match$&' 'Password entry trimmed, changed or mismatched its confirmation.'
Assert-Equal $script:answers.Count 0 'Unused private input answers.'
function Get-NetIPConfiguration {
    [pscustomobject]@{IPv4Address=@([pscustomobject]@{IPAddress='192.0.2.10'});IPv4DefaultGateway=[pscustomobject]@{NextHop='192.0.2.1'}}
}
$fixtureRoot = Join-Path (Split-Path -Parent $PSScriptRoot) ('runtime\setup-wizard-' + [Guid]::NewGuid().ToString('N'))
function New-PreparedFixture {
    param([string]$Name)
    $root=Join-Path $fixtureRoot $Name
    foreach ($folder in @('cstrike\addons\statsme\dlls','cstrike\addons\yapb\conf','cstrike\addons\amxmodx\configs')) { New-Item -Path (Join-Path $root $folder) -ItemType Directory -Force | Out-Null }
    [IO.File]::WriteAllBytes((Join-Path $root 'cstrike\addons\statsme\dlls\sm_cstrike_mm.dll'),[byte[]]@())
    'sm_rankbots 1' | Set-Content -LiteralPath (Join-Path $root 'cstrike\addons\statsme\statsme.cfg') -Encoding ascii
    @('yb_quota "0"','yb_password ""','yb_password_key "_ybpw"') | Set-Content -LiteralPath (Join-Path $root 'cstrike\addons\yapb\conf\yapb.cfg') -Encoding ascii
    return $root
}
$server = New-PreparedFixture 'interactive'
$amx='Amx$&$1$$'
$yb='Yb$&$1$$''T'
$rcon='Rcon%&$1'
Set-Answers ($recommended + @($amx,$amx,$yb,$yb,$rcon,$rcon))
$messages = @(& (Join-Path $PSScriptRoot 'Configure-CS15Server.ps1') -ServerDirectory $server -BindAddress '192.0.2.10' 6>&1)
Assert-Equal $script:answers.Count 0 'Interactive setup did not consume all credentials.'
$privatePrompts = @($script:prompts | Where-Object { $_ -match '^1[234]\.' })
Assert-Equal ($privatePrompts -join '|') '12. AMX password|13. YaPB password|14. RCON password' 'Private questions were asked out of order.'
$publicText = [IO.File]::ReadAllText((Join-Path $server 'settings.local.json'))
foreach ($secret in @($amx,$yb,$rcon)) {
    if ($publicText.Contains($secret) -or (($messages | Out-String).Contains($secret))) { throw 'A password escaped into public settings or console output.' }
}
if (-not ([IO.File]::ReadAllText((Join-Path $server 'cstrike\addons\amxmodx\configs\users.ini'))).Contains('"' + $amx + '"')) { throw 'AMX credential changed.' }
if (-not ([IO.File]::ReadAllText((Join-Path $server 'cstrike\addons\yapb\conf\yapb.cfg'))).Contains('yb_password "' + $yb + '"')) { throw 'YaPB credential changed.' }
if (-not ([IO.File]::ReadAllText((Join-Path $server 'cstrike\server.cfg'))).Contains('rcon_password "' + $rcon + '"')) { throw 'RCON credential changed.' }
if (-not ([IO.File]::ReadAllText((Join-Path $server 'ADMIN.local.txt'))).Contains('setinfo _ybpw "' + $yb + '"')) { throw 'YaPB client instructions missing.' }
$unattended = New-PreparedFixture 'unattended'
$settings | Add-Member -NotePropertyName AmxPassword -NotePropertyValue 'DO-NOT-COPY-PRIVATE-JSON'
$path=Join-Path $fixtureRoot 'input.local.json'
$settings | ConvertTo-Json | Set-Content -LiteralPath $path -Encoding ascii
Set-Answers @()
$null = & (Join-Path $PSScriptRoot 'Configure-CS15Server.ps1') -ServerDirectory $unattended -SettingsPath $path -BindAddress '192.0.2.10' 6>&1
$saved=Get-Content -LiteralPath (Join-Path $unattended 'settings.local.json') -Raw | ConvertFrom-Json
Assert-Equal @($saved.PSObject.Properties).Count 10 'Unattended settings included unknown/private fields.'
if ((Get-Content -LiteralPath (Join-Path $unattended 'settings.local.json') -Raw).Contains('DO-NOT-COPY')) { throw 'Imported private field was serialized.' }
Write-Host 'PASS: English wizard, aliases, custom values, skipped bot questions, confirmed masked credentials, literal password bytes and unattended/public-settings separation.'
