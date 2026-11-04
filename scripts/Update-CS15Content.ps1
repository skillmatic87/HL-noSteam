[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory = $true)][string]$ServerDirectory,
    [string]$ContentDirectory,
    [string]$CacheDirectory
)

. (Join-Path $PSScriptRoot 'CS15Content.Common.ps1')
$projectRoot = Split-Path -Parent $PSScriptRoot
if (-not $ContentDirectory) { $ContentDirectory = Join-Path $projectRoot 'content' }
if (-not $CacheDirectory) { $CacheDirectory = Join-Path $projectRoot 'downloads\content' }
$ServerDirectory = (Resolve-Path -LiteralPath $ServerDirectory).Path
$ContentDirectory = (Resolve-Path -LiteralPath $ContentDirectory).Path
$manifest = Get-CS15ContentManifest -ContentDirectory $ContentDirectory
foreach ($relative in @('hlds.exe','cstrike\liblist.gam','cstrike\mapcycle.txt','cstrike\addons\amxmodx\configs\maps.ini','cstrike\addons\amxmodx\configs\SND-LIST.CFG')) {
    if (-not (Test-Path -LiteralPath (Get-CS15ContentPath $ServerDirectory $relative) -PathType Leaf)) { throw ('Required installed server file is missing: ' + $relative) }
}
if ($WhatIfPreference) {
    [pscustomobject]@{ Pack=$manifest.id; Server=$ServerDirectory; Maps=@($manifest.maps).Count; Sounds=@($manifest.sounds).Count; Preview=$true }
    foreach ($map in $manifest.maps) { Write-Host ($map.name + ': up to ' + $map.maxPlayers + ' players') }
    return
}
Assert-CS15Stopped $ServerDirectory
if (-not $PSCmdlet.ShouldProcess($ServerDirectory, ('Install content pack ' + $manifest.id))) { return }

$CacheDirectory = [IO.Path]::GetFullPath($CacheDirectory)
$null = Get-CS15ContentPath $CacheDirectory 'cache-check'
New-Item -ItemType Directory -Path $CacheDirectory -Force | Out-Null
$files = New-Object Collections.Generic.List[object]
function Add-ContentBytes {
    param($Entry, [byte[]]$Bytes)
    if ((Get-CS15BytesHash $Bytes) -ne $Entry.sha256) { throw ('Content file checksum mismatch: ' + $Entry.target) }
    $files.Add([pscustomobject]@{Relative=$Entry.target; Bytes=$Bytes; Hash=$Entry.sha256; Preserve=[bool]$Entry.preserveExisting})
}
foreach ($entry in $manifest.localFiles) {
    $source = Get-CS15ContentPath $ContentDirectory $entry.source
    Add-ContentBytes $entry ([IO.File]::ReadAllBytes($source))
}
Add-Type -AssemblyName System.IO.Compression.FileSystem
foreach ($package in $manifest.packages) {
    $cached = Get-CS15ContentPath $CacheDirectory $package.file
    if (-not (Test-Path -LiteralPath $cached -PathType Leaf)) {
        $temporary = $cached + '.' + [Guid]::NewGuid().ToString('N') + '.partial'
        Write-Host ('Downloading ' + $package.file)
        & curl.exe --fail --location --silent --show-error --retry 2 --connect-timeout 20 --max-time 180 --output $temporary $package.url
        if ($LASTEXITCODE -ne 0) { throw ('Content download failed: ' + $package.file) }
        if ((Get-FileHash -LiteralPath $temporary).Hash -ine $package.sha256) { throw ('Downloaded content checksum mismatch: ' + $package.file) }
        Move-Item -LiteralPath $temporary -Destination $cached
    }
    if ((Get-FileHash -LiteralPath $cached).Hash -ine $package.sha256) { throw ('Cached content checksum mismatch: ' + $package.file) }
    if ($package.kind -eq 'raw') {
        if (@($package.files).Count -ne 1) { throw 'A raw package must contain exactly one file.' }
        Add-ContentBytes $package.files[0] ([IO.File]::ReadAllBytes($cached))
    } else {
        $archive = [IO.Compression.ZipFile]::OpenRead($cached)
        try {
            foreach ($entry in $package.files) {
                $matches = @($archive.Entries | Where-Object { $_.FullName.Replace('\','/') -ceq $entry.source })
                if ($matches.Count -ne 1 -or $matches[0].Length -gt 64MB) { throw ('Missing, duplicate or oversized archive member: ' + $entry.source) }
                $stream = $matches[0].Open()
                $memory = New-Object IO.MemoryStream
                try { $stream.CopyTo($memory); Add-ContentBytes $entry $memory.ToArray() } finally { $stream.Dispose(); $memory.Dispose() }
            }
        } finally { $archive.Dispose() }
    }
}

# Build the complete change set before modifying the installation.
$installedPath = Get-CS15ContentPath $ServerDirectory '_content/installed.json'
$previousHashes = @{}
if (Test-Path -LiteralPath $installedPath) {
    $previous = Get-Content -LiteralPath $installedPath -Raw | ConvertFrom-Json
    foreach ($entry in $previous.files) { $previousHashes[$entry.path] = $entry.sha256 }
}
$changes = New-Object Collections.Generic.List[object]
$managed = New-Object Collections.Generic.List[object]
foreach ($file in $files) {
    $target = Get-CS15ContentPath $ServerDirectory $file.Relative
    $managed.Add([pscustomobject]@{path=$file.Relative;sha256=$file.Hash})
    if (Test-Path -LiteralPath $target) {
        if (-not (Test-Path -LiteralPath $target -PathType Leaf)) { throw ('Content target is not a file: ' + $file.Relative) }
        $actual = (Get-FileHash -LiteralPath $target).Hash.ToLowerInvariant()
        if ($actual -eq $file.Hash) { continue }
        if ($file.Preserve) {
            $managed[$managed.Count - 1].sha256 = $actual
            Write-Host ('Keeping existing shared resource: ' + $file.Relative)
            continue
        }
        if (-not $previousHashes.ContainsKey($file.Relative) -or $actual -ne $previousHashes[$file.Relative]) { throw ('An existing file differs from the pack and was not overwritten: ' + $file.Relative) }
    }
    $changes.Add($file)
}
function Add-TextChange {
    param([string]$Relative, [string[]]$Lines)
    $target = Get-CS15ContentPath $ServerDirectory $Relative
    [byte[]]$bytes = [Text.Encoding]::ASCII.GetBytes(($Lines -join "`r`n") + "`r`n")
    $hash = Get-CS15BytesHash $bytes
    if (Test-Path -LiteralPath $target) { if ((Get-FileHash -LiteralPath $target).Hash -ieq $hash) { return } }
    $changes.Add([pscustomobject]@{Relative=$Relative;Bytes=$bytes;Hash=$hash;Preserve=$false})
}
function Add-AppendedText {
    param([string]$Relative, [string[]]$Additions)
    if (-not $Additions.Count) { return }
    $target = Get-CS15ContentPath $ServerDirectory $Relative
    [byte[]]$before = [IO.File]::ReadAllBytes($target)
    $separator = if ($before.Length -and $before[$before.Length - 1] -notin @(10,13)) { "`r`n" } else { '' }
    [byte[]]$bytes = $before + [Text.Encoding]::ASCII.GetBytes($separator + ($Additions -join "`r`n") + "`r`n")
    $changes.Add([pscustomobject]@{Relative=$Relative;Bytes=$bytes;Hash=(Get-CS15BytesHash $bytes);Preserve=$false})
}
foreach ($relative in @('cstrike/mapcycle.txt','cstrike/addons/amxmodx/configs/maps.ini')) {
    $lines = New-Object Collections.Generic.List[string]
    foreach ($line in [IO.File]::ReadAllLines((Get-CS15ContentPath $ServerDirectory $relative))) { $lines.Add($line) }
    $additions = New-Object Collections.Generic.List[string]
    foreach ($map in $manifest.maps) {
        $exists = @($lines | Where-Object { $_ -match ('^\s*"?' + [regex]::Escape($map.name) + '(?:"|\s|$)') }).Count -gt 0
        if (-not $exists) {
            if ($relative.EndsWith('maps.ini')) { $additions.Add(($map.name + ' 0 ' + $map.maxPlayers)) }
            else { $additions.Add(($map.name + ' "\minplayers\0\maxplayers\' + $map.maxPlayers + '"')) }
        }
    }
    Add-AppendedText $relative $additions.ToArray()
}
$soundRelative = 'cstrike/addons/amxmodx/configs/SND-LIST.CFG'
$soundLines = New-Object Collections.Generic.List[string]
foreach ($line in [IO.File]::ReadAllLines((Get-CS15ContentPath $ServerDirectory $soundRelative))) { $soundLines.Add($line) }
$soundAdditions = New-Object Collections.Generic.List[string]
foreach ($sound in $manifest.sounds) {
    $entries = @($soundLines | Where-Object { $_ -match ('^\s*' + [regex]::Escape($sound.keyword) + '\s*;') })
    if ($entries.Count) {
        foreach ($line in $entries) { $parts=$line.Split(';'); if ($parts.Count -ne 2 -or $parts[1].Trim() -ine $sound.path) { throw ('An existing sound keyword has a different mapping: ' + $sound.keyword) } }
    } else { $soundAdditions.Add(($sound.keyword + '; ' + $sound.path)) }
}
Add-AppendedText $soundRelative $soundAdditions.ToArray()
$installed = [ordered]@{schemaVersion=1;id=$manifest.id;files=$managed.ToArray();maps=@($manifest.maps.name);sounds=@($manifest.sounds.keyword)}
Add-TextChange '_content/installed.json' @($installed | ConvertTo-Json -Depth 6)
if ($changes.Count -eq 0) { Write-Host 'Content is already installed. No files changed.'; return }
Assert-CS15Stopped $ServerDirectory
$backupRelative = '_content/backups/' + [DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss') + '-' + [Guid]::NewGuid().ToString('N').Substring(0,8)
$backupRoot = Get-CS15ContentPath $ServerDirectory $backupRelative
New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null
$rollback = New-Object Collections.Generic.List[object]
foreach ($change in $changes) {
    $target = Get-CS15ContentPath $ServerDirectory $change.Relative
    $existed = Test-Path -LiteralPath $target -PathType Leaf
    if ($existed) {
        $saved = Get-CS15ContentPath $backupRoot ('files/' + $change.Relative)
        New-Item -ItemType Directory -Path (Split-Path -Parent $saved) -Force | Out-Null
        [IO.File]::Copy($target,$saved)
    }
    $rollback.Add([pscustomobject]@{path=$change.Relative;existed=$existed;installedSha256=$change.Hash})
}
$rollbackDocument = [ordered]@{schemaVersion=1;server=$ServerDirectory;files=$rollback.ToArray()}
$rollbackDocument | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $backupRoot 'rollback.json') -Encoding UTF8
$written = New-Object Collections.Generic.List[object]
try {
    foreach ($change in $changes) {
        $target = Get-CS15ContentPath $ServerDirectory $change.Relative
        New-Item -ItemType Directory -Path (Split-Path -Parent $target) -Force | Out-Null
        $written.Add($change)
        [IO.File]::WriteAllBytes($target,$change.Bytes)
    }
} catch {
    foreach ($change in $written) {
        $target = Get-CS15ContentPath $ServerDirectory $change.Relative
        $saved = Get-CS15ContentPath $backupRoot ('files/' + $change.Relative)
        if (Test-Path -LiteralPath $saved -PathType Leaf) { [IO.File]::Copy($saved,$target,$true) }
        elseif (Test-Path -LiteralPath $target -PathType Leaf) { Remove-Item -LiteralPath $target }
    }
    throw
}
[pscustomobject]@{Pack=$manifest.id;Maps=@($manifest.maps).Count;Sounds=@($manifest.sounds).Count;ChangedFiles=$changes.Count;Backup=$backupRoot}
