[CmdletBinding()]
param([string]$IntegrationCacheDirectory)

$ErrorActionPreference = 'Stop'
$cases = @(
    @{Name='Empty yes/no repeats';Kind='YesNo';Input=@('','y');Expected=1},
    @{Name='Only explicit yes/no tokens';Kind='YesNo';Input=@('1','true','I ACCEPT',' YES ');Expected=1},
    @{Name='Short no';Kind='YesNo';Input=@('N');Expected=0},
    @{Name='Full no';Kind='YesNo';Input=@('no');Expected=0},
    @{Name='German short yes';Kind='YesNo';Input=@(' J ');Expected=1},
    @{Name='German full yes';Kind='YesNo';Input=@('JA');Expected=1},
    @{Name='German full no';Kind='YesNo';Input=@('Nein');Expected=0},
    @{Name='Empty name repeats';Kind='Name';Input=@('','LAN server');Expected='LAN server'},
    @{Name='Unsafe name repeats';Kind='Name';Input=@('name;command','Admin');Expected='Admin'},
    @{Name='Reported server name with punctuation';Kind='ServerName';Input=@('oldsk00l CS1.5 amx,sounds, statsme, vote');Expected='oldsk00l CS1.5 amx,sounds, statsme, vote'},
    @{Name='Reported 32-character server name';Kind='ServerName';Input=@('oldsk00l CS1.5 sounds statsme vote');Expected='oldsk00l CS1.5 sounds statsme vote'},
    @{Name='Reported 33-character server name';Kind='ServerName';Input=@('oldschool CS15 statsme sounds vote');Expected='oldschool CS15 statsme sounds vote'},
    @{Name='63-character server name';Kind='ServerName';Input=@(('s' * 63));Expected=('s' * 63)},
    @{Name='Server name too long repeats';Kind='ServerName';Input=@(('s' * 64),'LAN server');Expected='LAN server'},
    @{Name='Player name still limited to 31';Kind='Name';Input=@(('p' * 32),('p' * 31));Expected=('p' * 31)},
    @{Name='Unsafe server name repeats';Kind='ServerName';Input=@('name;quit','LAN server');Expected='LAN server'},
    @{Name='Invalid number repeats';Kind='Integer';Input=@('','abc','-1','999999999999999999999','33','16');Expected=16},
    @{Name='Zero is a valid number';Kind='Integer';Input=@('0');Expected=0},
    @{Name='Ranking spelling normalized';Kind='RankScore';Input=@('','other','killsminusdeaths');Expected='KillsMinusDeaths'},
    @{Name='Ranking kills';Kind='RankScore';Input=@('kills');Expected='Kills'}
)
foreach ($case in $cases) {
    $responses = New-Object Collections.Queue
    foreach ($answer in $case.Input) { $responses.Enqueue($answer) }
    $readResponse = {
        param([string]$Prompt)
        if ($responses.Count -eq 0) { throw 'Unexpected extra setup prompt.' }
        $responses.Dequeue()
    }.GetNewClosure()
    Set-Item -Path Function:Read-Host -Value $readResponse
    $result = & (Join-Path $PSScriptRoot 'Read-CS15SetupInput.ps1') -Prompt $case.Name -Kind $case.Kind
    if ($result -cne $case.Expected -or $responses.Count -ne 0) { throw ('Failed: ' + $case.Name) }
    Write-Host ('PASS: ' + $case.Name)
}
Write-Host 'All setup input checks passed.'

if ($IntegrationCacheDirectory) {
    $projectRoot = Split-Path -Parent $PSScriptRoot
    $fixture = Join-Path $projectRoot ('runtime\configuration-resume-' + [Guid]::NewGuid().ToString('N'))
    $responses = New-Object Collections.Queue
    $responses.Enqueue($null)
    $readResponse = {
        param([string]$Prompt)
        if ($responses.Count -eq 0) { throw 'Unexpected setup prompt.' }
        $responses.Dequeue()
    }.GetNewClosure()
    Set-Item -Path Function:Read-Host -Value $readResponse
    $interrupted = $false
    try {
        & (Join-Path $PSScriptRoot 'Install-CS15Server.ps1') -Destination $fixture -CacheDirectory $IntegrationCacheDirectory
    } catch {
        if ($_.Exception.Message -like 'Input ended.*') { $interrupted = $true } else { throw }
    }
    if (-not $interrupted -or -not (& (Join-Path $PSScriptRoot 'Test-CS15PreparedSetup.ps1') -ServerDirectory $fixture)) {
        throw 'Interrupted setup did not retain resumable prepared files.'
    }
    $userFile = Join-Path $fixture 'cstrike\addons\amxmodx\configs\users.ini'
    Add-Content -LiteralPath $userFile -Value '; Operator edit must be protected.' -Encoding ascii
    if (& (Join-Path $PSScriptRoot 'Test-CS15PreparedSetup.ps1') -ServerDirectory $fixture) { throw 'Edited operator configuration was not protected.' }
    Copy-Item -LiteralPath (Join-Path $fixture '_setup\amxx\addons\amxmodx\configs\users.ini') -Destination $userFile -Force
    $extractionsBefore = @(Get-ChildItem -LiteralPath (Join-Path $fixture '_setup') -Directory -Filter 'server-*').Count
    $responses = New-Object Collections.Queue
    foreach ($answer in @('','Interactive regression','oops','n','6','','maybe','n','y','n','2','y','n','5','n','20','y','y','','TestAdmin','amx-fixture','amx-fixture','yb-fixture','yb-fixture','rcon-fixture','rcon-fixture')) { $responses.Enqueue($answer) }
    $readResponse = {
        param([string]$Prompt,[switch]$AsSecureString)
        if ($responses.Count -eq 0) { throw 'Unexpected setup prompt.' }
        $value = $responses.Dequeue()
        if ($AsSecureString) { return ConvertTo-SecureString -String $value -AsPlainText -Force }
        return $value
    }.GetNewClosure()
    Set-Item -Path Function:Read-Host -Value $readResponse
    & (Join-Path $PSScriptRoot 'Install-CS15Server.ps1') -Destination $fixture -CacheDirectory $IntegrationCacheDirectory
    if ($responses.Count -ne 0 -or -not (Test-Path -LiteralPath (Join-Path $fixture 'Start-CS15.cmd')) -or
        (Test-Path -LiteralPath (Join-Path $fixture '.install-incomplete'))) { throw 'Interactive configuration resume failed.' }
    if (@(Get-ChildItem -LiteralPath (Join-Path $fixture '_setup') -Directory -Filter 'server-*').Count -ne $extractionsBefore) {
        throw 'Resume unnecessarily extracted the server again.'
    }
    Write-Host 'PASS: interrupted configuration, protected operator edits, empty/invalid input, and resume without reinstalling or a license prompt.'
}
