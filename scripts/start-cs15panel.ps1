[CmdletBinding()]
param([string]$ServerDirectory)
$ErrorActionPreference = 'Stop'
try {
    $project = Split-Path -Parent $PSScriptRoot
    if (-not $ServerDirectory -and (Test-Path -LiteralPath (Join-Path $project 'CS15Server\Start-CS15.cmd'))) { $ServerDirectory = Join-Path $project 'CS15Server' }
    if ($ServerDirectory) { $ServerDirectory = (Resolve-Path -LiteralPath $ServerDirectory).Path }
    $panelHome = Join-Path $env:LOCALAPPDATA 'CS15ServerPanel'
    New-Item -ItemType Directory -Path $panelHome -Force | Out-Null
    $hash = [Security.Cryptography.SHA256]::Create()
    try { $id = ([BitConverter]::ToString($hash.ComputeHash([Text.Encoding]::UTF8.GetBytes(($project + '|' + $ServerDirectory).ToLowerInvariant())))).Replace('-','').Substring(0,16) } finally { $hash.Dispose() }
    $statePath = Join-Path $panelHome ('instance-' + $id + '.json')
    $browser = 'C:\Program Files\Google\Chrome\Application\chrome.exe'
    if (Test-Path -LiteralPath $statePath) {
        try {
            $saved = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
            if ($saved.url -match '^http://127\.0\.0\.1:[0-9]+/$') {
                $health = Invoke-RestMethod -Uri ($saved.url + 'health') -TimeoutSec 2
                if ($health.app -eq 'CS15-Local-Panel' -and $health.instance -eq $saved.instance) {
                    if (Test-Path -LiteralPath $browser) { Start-Process -FilePath $browser -ArgumentList $saved.url }
                    else { Start-Process $saved.url }
                    return
                }
            }
        } catch { }
    }
    $candidates = New-Object Collections.Generic.List[object]
    foreach ($name in @('py.exe','python.exe','python3.exe')) {
        $command = Get-Command $name -ErrorAction SilentlyContinue
        if ($command -and $command.Source -notlike '*\WindowsApps\*') {
            $prefix = if ($name -eq 'py.exe') { @('-3') } else { @() }
            $candidates.Add([pscustomobject]@{File=$command.Source;Prefix=$prefix})
        }
    }
    foreach ($candidate in @('C:\Python313\python.exe') + @(Get-ChildItem (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python*\python.exe') -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName)) {
        if (Test-Path -LiteralPath $candidate) { $candidates.Add([pscustomobject]@{File=$candidate;Prefix=@()}) }
    }
    $python = $null
    foreach ($candidate in $candidates) {
        $prefix = @($candidate.Prefix)
        & $candidate.File @prefix -c 'import sys;sys.exit(0 if sys.version_info >= (3,10) else 1)' 2>$null
        if ($LASTEXITCODE -eq 0) { $python=$candidate; break }
    }
    if (-not $python) { throw 'Python 3.10 or newer is required for the local panel. Install Python, then open the panel again.' }
    function Quote-PanelPath([string]$Value) { if ($Value.Contains('"')) { throw 'Invalid path.' }; '"' + $Value + '"' }
    $arguments = @($python.Prefix) + @((Quote-PanelPath (Join-Path $PSScriptRoot 'server_panel.py')), '--state-file', (Quote-PanelPath $statePath), '--open-browser')
    if ($ServerDirectory) { $arguments += @('--server',(Quote-PanelPath $ServerDirectory)) }
    if (Test-Path -LiteralPath $browser) { $arguments += @('--browser',(Quote-PanelPath $browser)) }
    $process = Start-Process -FilePath $python.File -ArgumentList $arguments -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $panelHome ('panel-' + $id + '.log')) -RedirectStandardError (Join-Path $panelHome ('panel-' + $id + '.error.log'))
    for ($attempt=0; $attempt -lt 60; $attempt++) {
        Start-Sleep -Milliseconds 200
        if (Test-Path -LiteralPath $statePath) {
            try {
                $saved=Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
                if ($saved.url -match '^http://127\.0\.0\.1:[0-9]+/$') {
                    $health=Invoke-RestMethod -Uri ($saved.url + 'health') -TimeoutSec 1
                    # py.exe may launch a separate python.exe child; compare the
                    # helper identity rather than the launcher's process ID.
                    if ($health.app -eq 'CS15-Local-Panel' -and $health.instance -eq $saved.instance) { return }
                }
            } catch { }
        }
        if ($process.HasExited) { break }
    }
    throw ('The local panel could not start. Diagnostic log: ' + (Join-Path $panelHome ('panel-' + $id + '.error.log')))
} catch {
    Add-Type -AssemblyName System.Windows.Forms
    [void][Windows.Forms.MessageBox]::Show($_.Exception.Message,'CS 1.5 local panel','OK','Error')
    exit 1
}
