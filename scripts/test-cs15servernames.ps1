$ErrorActionPreference = 'Stop'
function Get-NetIPConfiguration {
    [pscustomobject]@{ IPv4Address=@([pscustomobject]@{IPAddress='192.0.2.10'}); IPv4DefaultGateway=[pscustomobject]@{NextHop='192.0.2.1'} }
}
$project = Split-Path -Parent $PSScriptRoot
$fixtureRoot = Join-Path $project ('runtime\server-name-test-' + [Guid]::NewGuid().ToString('N'))
$cases = @(
    @{ServerName='oldsk00l CS1.5 amx,sounds, statsme, vote';AdminName='TestAdmin';Valid=$true},
    @{ServerName=('s' * 63);AdminName=('p' * 31);Valid=$true},
    @{ServerName=('s' * 64);AdminName='TestAdmin';Valid=$false;Error='maximum is 63'},
    @{ServerName='LAN';AdminName=('p' * 32);Valid=$false;Error='maximum is 31'},
    @{ServerName='name;quit';AdminName='TestAdmin';Valid=$false;Error='printable ASCII'}
)
for ($index=0; $index -lt $cases.Count; $index++) {
    $case=$cases[$index]
    $server=Join-Path $fixtureRoot ('case-' + $index)
    foreach ($folder in @('cstrike\addons\statsme\dlls','cstrike\addons\yapb\conf','cstrike\addons\amxmodx\configs')) {
        New-Item -Path (Join-Path $server $folder) -ItemType Directory -Force | Out-Null
    }
    [IO.File]::WriteAllBytes((Join-Path $server 'cstrike\addons\statsme\dlls\sm_cstrike_mm.dll'),[byte[]]@())
    'sm_rankbots 1' | Set-Content -LiteralPath (Join-Path $server 'cstrike\addons\statsme\statsme.cfg') -Encoding ascii
    'yb_quota 0' | Set-Content -LiteralPath (Join-Path $server 'cstrike\addons\yapb\conf\yapb.cfg') -Encoding ascii
    $settings=[ordered]@{ServerName=$case.ServerName;AdminName=$case.AdminName;MapMinutes=30;FriendlyFire=0;BotTarget=0;BotDifficulty=2;SoundCooldown=3;SoundQuota=100;RankBots=1;RankScore='KillsMinusDeaths'}
    $settingsPath=Join-Path $fixtureRoot ('input-' + $index + '.json')
    $settings | ConvertTo-Json | Set-Content -LiteralPath $settingsPath -Encoding ascii
    $failure=$null
    try { & (Join-Path $PSScriptRoot 'configure-cs15server.ps1') -ServerDirectory $server -SettingsPath $settingsPath -BindAddress '192.0.2.10' }
    catch { $failure=$_.Exception.Message }
    if ($case.Valid) {
        if ($failure) { throw $failure }
        $actual=[IO.File]::ReadAllText((Join-Path $server 'cstrike\server.cfg'))
        if (-not $actual.Contains('hostname "' + $case.ServerName + '"')) { throw 'Configured hostname was changed or truncated.' }
    } else {
        if (-not $failure -or $failure -notlike ('*' + $case.Error + '*')) { throw 'Invalid name did not produce the expected error.' }
        foreach ($path in @('settings.local.json','ADMIN.local.txt','cstrike\server.cfg','cstrike\addons\amxmodx\configs\users.ini')) {
            if (Test-Path -LiteralPath (Join-Path $server $path)) { throw 'Invalid settings created operator configuration.' }
        }
    }
}
Write-Host 'PASS: Windows configuration accepts complete 63-character server names, keeps admin names at 31, and rejects invalid input before writing credentials.'
