[CmdletBinding()]
param()
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'CS15Client.Common.ps1')
$testPrefix='Software\CS15ClientProfileTests\'
$testSubKey=$testPrefix+[Guid]::NewGuid().ToString('N')
$key=[Microsoft.Win32.Registry]::CurrentUser.CreateSubKey($testSubKey)
$licenseSentinel=[Guid]::NewGuid().ToString('N')
try {
    $key.SetValue('LicenseSentinel',$licenseSentinel)
    $key.SetValue('AudioPreference',17,[Microsoft.Win32.RegistryValueKind]::DWord)
    Set-CS15VideoSettings -Width 1920 -Height 1080 -RegistrySubKey $testSubKey
    Set-CS15VideoSettings -Width 2560 -Height 1440 -RegistrySubKey $testSubKey
    if($key.GetValue('LicenseSentinel') -ne $licenseSentinel -or $key.GetValue('AudioPreference') -ne 17) { throw 'An unrelated registry value was changed.' }
    if($key.GetValue('EngineModeW') -ne 2560 -or $key.GetValue('EngineModeH') -ne 1440 -or $key.GetValue('EngineModeBPP') -ne 32) { throw 'Video preferences were not updated.' }
    if($key.GetValueNames().Count -ne 8) { throw 'Unexpected registry values were removed or added.' }
    Write-Host 'PASS: repeated resolution changes preserve unrelated credential and audio values.'
} finally {
    $key.Dispose()
    if($testSubKey.StartsWith($testPrefix,[StringComparison]::Ordinal) -and $testSubKey.Length -eq $testPrefix.Length+32) {
        [Microsoft.Win32.Registry]::CurrentUser.DeleteSubKey($testSubKey)
    }
}
