[CmdletBinding()]
param([string]$CacheDirectory)
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'CS15Content.Common.ps1')
$project=Split-Path -Parent $PSScriptRoot
if (-not $CacheDirectory) { $CacheDirectory=Join-Path $project 'downloads\content' }
$content=Join-Path $project 'content'
$manifest=Get-CS15ContentManifest $content
$fixture=Join-Path $project ('runtime\content-test-'+[Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $fixture -Force | Out-Null
function Write-Fixture {
    param([string]$Relative,[byte[]]$Bytes)
    $path=Get-CS15ContentPath $fixture $Relative
    New-Item -ItemType Directory -Path (Split-Path -Parent $path) -Force | Out-Null
    [IO.File]::WriteAllBytes($path,$Bytes)
}
function Assert-True { param([bool]$Condition,[string]$Message) if (-not $Condition) { throw $Message } }
function Get-FixtureSnapshot {
    $snapshot=@{}
    foreach ($file in Get-ChildItem -LiteralPath $fixture -Recurse -File) {
        if ($file.FullName -like ($fixture+'\_content\backups\*')) { continue }
        $snapshot[$file.FullName.Substring($fixture.Length+1)]=(Get-FileHash -LiteralPath $file.FullName).Hash
    }
    $snapshot
}
function Assert-Snapshot { param($Before,$After)
    Assert-True ($Before.Count -eq $After.Count) 'The fixture file count changed unexpectedly.'
    foreach ($key in $Before.Keys) { Assert-True ($After[$key] -eq $Before[$key]) ('File changed unexpectedly: '+$key) }
}
foreach ($path in @('hlds.exe','cstrike/liblist.gam','cstrike/server.cfg','cstrike/addons/amxmodx/configs/users.ini','cstrike/statsme.log','cstrike/addons/statsme/statsme.log')) {
    Write-Fixture $path ([Text.Encoding]::ASCII.GetBytes('Fixture sentinel: '+$path))
}
$cycleBytes=[byte[]](@(239,187,191)+[Text.Encoding]::UTF8.GetBytes("// Preserve original Unicode: Gr$([char]252)$([char]223)e`nde_dust2"))
Write-Fixture 'cstrike/mapcycle.txt' $cycleBytes
Write-Fixture 'cstrike/addons/amxmodx/configs/maps.ini' ([Text.Encoding]::ASCII.GetBytes("; Operator entry`r`nde_dust2`r`n"))
Write-Fixture 'cstrike/addons/amxmodx/configs/SND-LIST.CFG' ([Text.Encoding]::ASCII.GetBytes("SND_MAX; 100`r`nSND_DELAY; 3`r`nheadshot; sound/misc/headshot.wav`r`n"))
$stockMotd = [Text.Encoding]::ASCII.GetBytes("You are playing Counter-Strike v1.5`nVisit the official CS web site @`nwww.counter-strike.net")
Write-Fixture 'cstrike/motd.txt' $stockMotd
Write-Fixture 'cstrike/gfx/env/snowup.tga' ([Text.Encoding]::ASCII.GetBytes('Keep an existing shared resource.'))
$initial=Get-FixtureSnapshot
$null=& (Join-Path $PSScriptRoot 'Update-CS15Content.ps1') -ServerDirectory $fixture -CacheDirectory $CacheDirectory -WhatIf
Assert-Snapshot $initial (Get-FixtureSnapshot)
Write-Host 'PASS: preview does not modify the server.'
foreach ($path in @('../outside','cstrike/../../outside','C:\outside','sound/test:stream','cstrike//maps')) {
    $rejected=$false
    try { $null=Get-CS15ContentPath $fixture $path } catch { $rejected=$true }
    Assert-True $rejected ('Unsafe path accepted: '+$path)
}
Write-Host 'PASS: relative-path containment checks.'
Write-Fixture 'cstrike/maps/awp_map.bsp' ([Text.Encoding]::ASCII.GetBytes('Operator map must survive.'))
$conflictBefore=Get-FixtureSnapshot
$rejected=$false
try { & (Join-Path $PSScriptRoot 'Update-CS15Content.ps1') -ServerDirectory $fixture -CacheDirectory $CacheDirectory | Out-Null } catch {
    if ($_.Exception.Message -like 'An existing file differs*') { $rejected=$true } else { throw }
}
Assert-True $rejected 'A conflicting map was not rejected.'
Assert-Snapshot $conflictBefore (Get-FixtureSnapshot)
Remove-Item -LiteralPath (Get-CS15ContentPath $fixture 'cstrike/maps/awp_map.bsp')
Write-Host 'PASS: conflicting map is rejected before any server files change.'

Write-Fixture 'cstrike/motd.txt' ([Text.Encoding]::ASCII.GetBytes('Operator MOTD must survive.'))
$customBefore=Get-FixtureSnapshot
$rejected=$false
try { & (Join-Path $PSScriptRoot 'Update-CS15Content.ps1') -ServerDirectory $fixture -CacheDirectory $CacheDirectory | Out-Null } catch {
    if ($_.Exception.Message -like 'An existing file differs*motd.txt') { $rejected=$true } else { throw }
}
Assert-True $rejected 'A custom MOTD was not protected.'
Assert-Snapshot $customBefore (Get-FixtureSnapshot)
Write-Fixture 'cstrike/motd.txt' $stockMotd
Write-Host 'PASS: custom MOTD is rejected before mutation; known stock MOTD remains eligible.'

$corrupt=Join-Path $project ('runtime\corrupt-content-'+[Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $corrupt -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $content 'files') -Destination $corrupt -Recurse
$bad=Get-Content -LiteralPath (Join-Path $content 'pack.json') -Raw | ConvertFrom-Json
$bad.localFiles[0].sha256=('0'*64)
$bad | ConvertTo-Json -Depth 12 | Set-Content (Join-Path $corrupt 'pack.json') -Encoding UTF8
$rejected=$false
try { & (Join-Path $PSScriptRoot 'Update-CS15Content.ps1') -ServerDirectory $fixture -ContentDirectory $corrupt -CacheDirectory $CacheDirectory | Out-Null } catch {
    if ($_.Exception.Message -like 'Content file checksum mismatch*') { $rejected=$true } else { throw }
}
Assert-True $rejected 'Corrupt local content was not rejected.'
Assert-Snapshot $initial (Get-FixtureSnapshot)
Write-Host 'PASS: corrupt content is rejected before server mutation.'

$result=& (Join-Path $PSScriptRoot 'Update-CS15Content.ps1') -ServerDirectory $fixture -CacheDirectory $CacheDirectory
Assert-True ($result.ChangedFiles -gt 0) 'No content was installed.'
Assert-True (@(Get-ChildItem (Join-Path $fixture 'cstrike\maps') -Filter '*.bsp').Count -eq 13) 'Expected thirteen additional maps.'
Assert-True (@(Get-ChildItem (Join-Path $fixture 'cstrike\sound\lan') -Filter '*.wav').Count -eq @($manifest.sounds).Count) 'Expected every sound listed in the content manifest.'
$after=Get-FixtureSnapshot
foreach ($path in @('hlds.exe','cstrike\liblist.gam','cstrike\server.cfg','cstrike\addons\amxmodx\configs\users.ini','cstrike\statsme.log','cstrike\addons\statsme\statsme.log','cstrike\gfx\env\snowup.tga')) {
    Assert-True ($initial[$path] -eq $after[$path]) ('An unrelated file was modified: '+$path)
}
[byte[]]$updatedCycle=[IO.File]::ReadAllBytes((Join-Path $fixture 'cstrike\mapcycle.txt'))
Assert-True ([Convert]::ToBase64String($updatedCycle[0..($cycleBytes.Length-1)]) -eq [Convert]::ToBase64String($cycleBytes)) 'Original Unicode or line endings were changed.'
$soundText=[IO.File]::ReadAllText((Join-Path $fixture 'cstrike\addons\amxmodx\configs\SND-LIST.CFG'))
Assert-True ($soundText.StartsWith("SND_MAX; 100`r`nSND_DELAY; 3`r`n")) 'Local sound quota or delay changed.'
Assert-True ($soundText -match '(?m)^SND_JOIN; sound/lan/welcome\.wav\r?$') 'Welcome join sound is missing.'
foreach ($relative in @('cstrike/motd.txt','cstrike/addons/yapb/conf/lang/en_chat.cfg')) {
    $entry = @($manifest.localFiles | Where-Object { $_.target -eq $relative })[0]
    Assert-True ((Get-FileHash -LiteralPath (Get-CS15ContentPath $fixture $relative)).Hash -ieq $entry.sha256) ('Shared presentation file differs: ' + $relative)
}
$mapsText=[IO.File]::ReadAllText((Join-Path $fixture 'cstrike\addons\amxmodx\configs\maps.ini'))
Assert-True ($mapsText -match '(?m)^de_rats_2001 0 20\r?$') 'Rats 2001 capacity is missing.'
Write-Host ('PASS: thirteen maps and '+@($manifest.sounds).Count+' sounds installed; credentials, ranking, original text and shared resources preserved.')
$null=& (Join-Path $PSScriptRoot 'Update-CS15Content.ps1') -ServerDirectory $fixture -CacheDirectory $CacheDirectory
Assert-Snapshot $after (Get-FixtureSnapshot)
Write-Host 'PASS: a second update makes no changes and adds no duplicate entries.'

$soundPath=Get-CS15ContentPath $fixture 'cstrike/addons/amxmodx/configs/SND-LIST.CFG'
[byte[]]$soundBefore=[IO.File]::ReadAllBytes($soundPath)
[IO.File]::WriteAllText($soundPath,$soundText.Replace('SND_JOIN; sound/lan/welcome.wav','SND_JOIN;'),[Text.Encoding]::ASCII)
$null=& (Join-Path $PSScriptRoot 'Update-CS15Content.ps1') -ServerDirectory $fixture -CacheDirectory $CacheDirectory
Assert-Snapshot $after (Get-FixtureSnapshot)
[IO.File]::WriteAllText($soundPath,$soundText.Replace('SND_JOIN; sound/lan/welcome.wav','SND_JOIN; sound/custom/operator.wav'),[Text.Encoding]::ASCII)
$customJoin=Get-FixtureSnapshot
$null=& (Join-Path $PSScriptRoot 'Update-CS15Content.ps1') -ServerDirectory $fixture -CacheDirectory $CacheDirectory
Assert-Snapshot $customJoin (Get-FixtureSnapshot)
[IO.File]::WriteAllBytes($soundPath,$soundBefore)
Write-Host 'PASS: blank join setting is filled; a custom join sound is preserved.'

$changedSound=Join-Path $fixture 'cstrike\sound\lan\moin.wav'
$originalSound=[IO.File]::ReadAllBytes($changedSound)
[IO.File]::WriteAllText($changedSound,'A subsequent operator edit.')
$edited=Get-FixtureSnapshot
$rejected=$false
try { & (Join-Path $PSScriptRoot 'Restore-CS15Content.ps1') -ServerDirectory $fixture -BackupDirectory $result.Backup } catch {
    if ($_.Exception.Message -like 'A file changed after this update*') { $rejected=$true } else { throw }
}
Assert-True $rejected 'Restore did not protect a subsequent operator edit.'
Assert-Snapshot $edited (Get-FixtureSnapshot)
[IO.File]::WriteAllBytes($changedSound,$originalSound)
& (Join-Path $PSScriptRoot 'Restore-CS15Content.ps1') -ServerDirectory $fixture -BackupDirectory $result.Backup
Assert-Snapshot $initial (Get-FixtureSnapshot)
Write-Host 'PASS: restore protects later edits and otherwise restores the exact original files.'
Write-Host ('Content integration checks passed. Fixture retained at '+$fixture)
