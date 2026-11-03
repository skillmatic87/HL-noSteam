[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$fixtureRoot = Join-Path (Split-Path -Parent $PSScriptRoot) ('runtime\license-test-' + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $fixtureRoot -Force | Out-Null
$licensePath = Join-Path $fixtureRoot 'license.txt'
'Test fixture only; no software license is accepted by this test.' | Set-Content -LiteralPath $licensePath -Encoding ascii

$cases = @(
    @{Name='Exact explicit acceptance';Input=@('I ACCEPT');Expected=$true},
    @{Name='Whitespace and case';Input=@('  i   AcCePt  ');Expected=$true},
    @{Name='Empty and invalid input reprompt';Input=@('','accept','I ACCEPT');Expected=$true},
    @{Name='Empty input never accepts';Input=@('','CANCEL');Expected=$false},
    @{Name='Explicit cancellation';Input=@('cancel');Expected=$false},
    @{Name='No declines';Input=@('NO');Expected=$false},
    @{Name='End of input declines';Input=@($null);Expected=$false}
)
foreach ($case in $cases) {
    $responses = New-Object System.Collections.Queue
    foreach ($answer in $case.Input) { $responses.Enqueue($answer) }
    # The closure retains this queue when the helper runs in a child script scope.
    $readResponse = {
        param([string]$Prompt)
        if ($responses.Count -eq 0) { throw 'Unexpected extra license prompt.' }
        $responses.Dequeue()
    }.GetNewClosure()
    Set-Item -Path Function:Read-Host -Value $readResponse
    $accepted = & (Join-Path $PSScriptRoot 'Confirm-CS15ServerLicense.ps1') -LicensePath $licensePath
    if ($accepted -ne $case.Expected -or $responses.Count -ne 0) { throw ('Failed: ' + $case.Name) }
    Write-Host ('PASS: ' + $case.Name)
}
Write-Host 'All license interaction checks passed.'
