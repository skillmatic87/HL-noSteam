$ErrorActionPreference = 'Stop'

function Assert-CS15SetupPassword {
    param([AllowEmptyString()][string]$Value)
    if ($Value.Length -lt 1 -or $Value.Length -gt 31 -or $Value -match '[^\x21-\x7e]|[";\\]') {
        throw 'Passwords must use 1-31 printable ASCII characters without spaces, quotes, semicolons or backslashes.'
    }
}

function New-CS15SetupPassword {
    $random = [Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $bytes = New-Object byte[] 15
        $random.GetBytes($bytes)
        return -join ($bytes | ForEach-Object { $_.ToString('x2') })
    } finally { $random.Dispose() }
}

function Read-CS15PrivateText {
    param([string]$Prompt)
    $secret = Read-Host -Prompt $Prompt -AsSecureString
    if ($null -eq $secret) { throw 'Password input ended. Run Setup.cmd again to continue.' }
    $pointer = [IntPtr]::Zero
    try {
        $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secret)
        return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
    } finally {
        if ($pointer -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer) }
        $secret.Dispose()
    }
}

function Read-CS15SetupPassword {
    param([string]$Prompt)
    while ($true) {
        $value = Read-CS15PrivateText $Prompt
        try { Assert-CS15SetupPassword $value }
        catch { Write-Host $_.Exception.Message; continue }
        $confirmation = Read-CS15PrivateText 'Confirm password'
        if ($value -cne $confirmation) {
            Write-Host 'Passwords do not match. Please enter the password again.'
            continue
        }
        return $value
    }
}

function Get-CS15SetupCredentials {
    param([switch]$Automatic)
    if ($Automatic) {
        return @{AmxPassword=(New-CS15SetupPassword);YbPassword=(New-CS15SetupPassword);RconPassword=(New-CS15SetupPassword)}
    }
    return @{
        AmxPassword=(Read-CS15SetupPassword '12. AMX password')
        YbPassword=(Read-CS15SetupPassword '13. YaPB password')
        RconPassword=(Read-CS15SetupPassword '14. RCON password')
    }
}

function Set-CS15LiteralCvar {
    param([string]$Text,[string]$Name,[string]$Value)
    $pattern = '(?m)^([ \t]*' + [regex]::Escape($Name) + '[ \t]+)(?:"[^"\r\n]*"|[^\s;]+)([^\r\n]*)'
    $matches = [regex]::Matches($Text,$pattern)
    if ($matches.Count -gt 1) { throw ('Multiple active settings found for ' + $Name + '.') }
    if ($matches.Count -eq 0) {
        $newline = if ($Text.Contains("`r`n")) { "`r`n" } else { "`n" }
        $separator = if ($Text -and $Text -notmatch '[\r\n]$') { $newline } else { '' }
        return $Text + $separator + $Name + ' "' + $Value + '"' + $newline
    }
    $replacement = { param($match) $match.Groups[1].Value + '"' + $Value + '"' + $match.Groups[2].Value }.GetNewClosure()
    return [regex]::Replace($Text,$pattern,[Text.RegularExpressions.MatchEvaluator]$replacement)
}
