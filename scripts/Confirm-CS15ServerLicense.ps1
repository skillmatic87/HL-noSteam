[CmdletBinding()]
param([Parameter(Mandatory = $true)][string]$LicensePath)

$ErrorActionPreference = 'Stop'
Get-Content -LiteralPath $LicensePath | Out-Host
Write-Host ''
Write-Host 'Read the server license above (also saved as SERVER-LICENSE.txt).'
Write-Host 'Type I ACCEPT to agree, or CANCEL to stop. Pressing Enter does not accept.'
while ($true) {
    $response = Read-Host 'Your choice: I ACCEPT / CANCEL'
    if ($null -eq $response) { return $false }
    $response = ($response.Trim() -replace '\s+', ' ')
    if ($response -ieq 'I ACCEPT') { return $true }
    if ($response -iin @('CANCEL','NO','N')) { return $false }
    Write-Host 'No choice was recorded. Type I ACCEPT to agree, or CANCEL to stop.'
}
