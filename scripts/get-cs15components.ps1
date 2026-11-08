[CmdletBinding()]
param([string]$CacheDirectory)

$ErrorActionPreference = 'Stop'
if (-not $CacheDirectory) { $CacheDirectory = Join-Path (Split-Path -Parent $PSScriptRoot) 'downloads\packages' }
$manifest = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'components.json') -Raw | ConvertFrom-Json
if ($manifest.schemaVersion -ne 1) { throw 'Unsupported component manifest.' }
New-Item -ItemType Directory -Path $CacheDirectory -Force | Out-Null
$CacheDirectory = (Resolve-Path -LiteralPath $CacheDirectory).Path
$components = @{}
foreach ($item in $manifest.components) {
    if ($item.file -ne [IO.Path]::GetFileName($item.file) -or $item.sha256 -notmatch '^[a-f0-9]{64}$' -or $item.url -notmatch '^https://') {
        throw 'Invalid component manifest entry.'
    }
    $target = Join-Path $CacheDirectory $item.file
    if (Test-Path -LiteralPath $target) {
        if ((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash -ine $item.sha256) {
            throw ('Cached file has the wrong SHA-256. Move it aside and retry: ' + $target)
        }
    } else {
        Write-Host ('Downloading ' + $item.file)
        $temporary = $target + '.' + [Guid]::NewGuid().ToString('N') + '.partial'
        & curl.exe --fail --location --silent --show-error --retry 2 --connect-timeout 30 --max-time 900 --output $temporary $item.url
        if ($LASTEXITCODE -ne 0) { throw ('Download failed: ' + $item.file) }
        if ((Get-FileHash -LiteralPath $temporary -Algorithm SHA256).Hash -ine $item.sha256) { throw ('Downloaded file has the wrong SHA-256: ' + $item.file) }
        Move-Item -LiteralPath $temporary -Destination $target
    }
    $components[$item.id] = $target
}
$components
