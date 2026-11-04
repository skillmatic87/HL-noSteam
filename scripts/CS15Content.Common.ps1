$ErrorActionPreference = 'Stop'

function Get-CS15ContentPath {
    param([string]$Root, [string]$Relative)
    if ([string]::IsNullOrWhiteSpace($Relative) -or $Relative -match '[<>:"|?*\x00-\x1f]' -or
        [IO.Path]::IsPathRooted($Relative) -or @($Relative -split '[/\\]' | Where-Object { $_ -in @('','.', '..') }).Count) {
        throw ('Invalid relative content path: ' + $Relative)
    }
    $base = [IO.Path]::GetFullPath($Root).TrimEnd('\') + '\'
    $full = [IO.Path]::GetFullPath((Join-Path $base $Relative))
    if (-not $full.StartsWith($base, [StringComparison]::OrdinalIgnoreCase)) { throw 'Content path escapes its root.' }
    $check = $full
    while ($check -and $check.Length -ge $base.TrimEnd('\').Length) {
        if (Test-Path -LiteralPath $check) {
            if ((Get-Item -LiteralPath $check -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) { throw ('Content path contains a link: ' + $check) }
        }
        $check = Split-Path -Parent $check
    }
    $full
}

function Get-CS15BytesHash {
    param([byte[]]$Bytes)
    $hash = [Security.Cryptography.SHA256]::Create()
    try { ([BitConverter]::ToString($hash.ComputeHash($Bytes))).Replace('-','').ToLowerInvariant() } finally { $hash.Dispose() }
}

function Assert-CS15Stopped {
    param([string]$ServerDirectory)
    $executable = Join-Path $ServerDirectory 'hlds.exe'
    foreach ($process in @(Get-CimInstance Win32_Process -Filter "Name = 'hlds.exe'")) {
        if (-not $process.ExecutablePath) { throw 'Cannot determine the path of a running HLDS process. Stop HLDS before updating.' }
        if ($process.ExecutablePath -ieq $executable) { throw 'This server is running. Quit it cleanly before applying or restoring content.' }
    }
}

function Get-CS15ContentManifest {
    param([string]$ContentDirectory)
    $manifest = Get-Content -LiteralPath (Join-Path $ContentDirectory 'pack.json') -Raw | ConvertFrom-Json
    if ($manifest.schemaVersion -ne 1 -or $manifest.id -notmatch '^[a-z0-9-]+$') { throw 'Invalid content manifest.' }
    $targets = @{}
    foreach ($file in @($manifest.localFiles) + @($manifest.packages | ForEach-Object { $_.files })) {
        $presentationTarget = $file.target -in @('cstrike/motd.txt','cstrike/addons/yapb/conf/lang/en_chat.cfg')
        if ($file.sha256 -notmatch '^[a-f0-9]{64}$' -or (-not $presentationTarget -and $file.target -notmatch '^(cstrike/(maps/|sound/|gfx/env/|models/|sprites/|overviews/|addons/yapb/data/(graph|pwf)/)|_content/notices/)')) { throw 'Invalid content file entry.' }
        if ($file.replaceExistingSha256) {
            if (-not $presentationTarget) { throw 'Known-file replacement is limited to the MOTD and English bot chat.' }
            foreach ($hash in $file.replaceExistingSha256) { if ($hash -notmatch '^[a-f0-9]{64}$') { throw 'Invalid known-file checksum.' } }
        }
        $null = Get-CS15ContentPath -Root $ContentDirectory -Relative $file.target
        if ($targets.ContainsKey($file.target)) { throw ('Duplicate content target: ' + $file.target) }
        $targets[$file.target] = $true
    }
    foreach ($package in $manifest.packages) {
        if ($package.file -ne [IO.Path]::GetFileName($package.file) -or $package.url -notmatch '^https://' -or $package.sha256 -notmatch '^[a-f0-9]{64}$' -or $package.kind -notin @('zip','raw')) { throw 'Invalid content download entry.' }
    }
    $mapNames = @{}
    foreach ($map in $manifest.maps) {
        if ($map.name -notmatch '^[a-z0-9_-]{1,31}$' -or $map.maxPlayers -lt 2 -or $map.maxPlayers -gt 32 -or $mapNames.ContainsKey($map.name) -or -not $targets.ContainsKey(('cstrike/maps/' + $map.name + '.bsp'))) { throw 'Invalid, duplicate or missing content map entry.' }
        $mapNames[$map.name] = $true
    }
    $keywords = @{}
    foreach ($sound in $manifest.sounds) {
        if ($sound.keyword -notmatch '^[a-z0-9_-]{1,30}$' -or $sound.path -notmatch '^sound/lan/[a-z0-9_-]+\.wav$' -or $keywords.ContainsKey($sound.keyword) -or -not $targets.ContainsKey(('cstrike/' + $sound.path))) { throw 'Invalid, duplicate or missing sound trigger.' }
        $keywords[$sound.keyword] = $true
    }
    if ($manifest.joinSound -and ($manifest.joinSound -notin @($manifest.sounds.path))) { throw 'Join sound must be a verified sound in this pack.' }
    $manifest
}
