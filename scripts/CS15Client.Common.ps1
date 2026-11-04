function Set-CS15VideoSettings {
    param(
        [ValidateRange(640,16384)][int]$Width,
        [ValidateRange(480,16384)][int]$Height,
        [bool]$Windowed = $false,
        [string]$RegistrySubKey = 'Software\Valve\Half-Life\Settings'
    )
    # CreateSubKey opens an existing key without replacing its other values.
    # Never recreate Settings with the registry provider's New-Item -Force.
    $key=[Microsoft.Win32.Registry]::CurrentUser.CreateSubKey($RegistrySubKey)
    try {
        foreach ($setting in @(@('EngineModeW',$Width),@('EngineModeH',$Height),@('EngineModeBPP',32),@('EngineModeWindowed',[int]$Windowed),@('ScreenWindowed',[int]$Windowed))) {
            $key.SetValue($setting[0],[int]$setting[1],[Microsoft.Win32.RegistryValueKind]::DWord)
        }
        $key.SetValue('EngineDLL','hw.dll',[Microsoft.Win32.RegistryValueKind]::String)
    } finally { $key.Dispose() }
}
