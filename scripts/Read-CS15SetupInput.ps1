[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Prompt,
    [Parameter(Mandatory = $true)][ValidateSet('YesNo','Name','Integer','RankScore')][string]$Kind,
    [int]$Minimum = 0,
    [int]$Maximum = 32
)

$ErrorActionPreference = 'Stop'
$hint = switch ($Kind) {
    'YesNo' { 'yes/y or no/n' }
    'Name' { '1-31 printable ASCII characters; no quotes, semicolons or backslashes' }
    'Integer' { [string]$Minimum + '-' + [string]$Maximum }
    'RankScore' { 'KillsMinusDeaths or Kills' }
}
while ($true) {
    $answer = Read-Host ($Prompt + ' [' + $hint + ']')
    if ($null -eq $answer) { throw 'Input ended. Run Setup.cmd again to continue configuring this server.' }
    $answer = $answer.Trim()
    if ($answer.Length -gt 0) {
        switch ($Kind) {
            'YesNo' {
                if ($answer -iin @('yes','y')) { return 1 }
                if ($answer -iin @('no','n')) { return 0 }
            }
            'Name' {
                if ($answer.Length -le 31 -and $answer -notmatch '[^\x20-\x7e]|[";\\]') { return $answer }
            }
            'Integer' {
                $number = 0
                if ($answer -match '^\d+$' -and [int]::TryParse($answer,[ref]$number) -and $number -ge $Minimum -and $number -le $Maximum) { return $number }
            }
            'RankScore' {
                if ($answer -ieq 'KillsMinusDeaths') { return 'KillsMinusDeaths' }
                if ($answer -ieq 'Kills') { return 'Kills' }
            }
        }
    }
    Write-Host ('Please enter ' + $hint + '. Empty input does not select a value.')
}
