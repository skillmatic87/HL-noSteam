[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms
if (-not ('CS15DisplayQuery' -as [type])) {
    Add-Type @'
using System;
using System.Runtime.InteropServices;
public static class CS15DisplayQuery {
    [DllImport("user32.dll", CharSet=CharSet.Unicode, EntryPoint="EnumDisplaySettingsW")]
    public static extern bool EnumDisplaySettings(string name, int mode, IntPtr data);
}
'@
}
$primary = [Windows.Forms.Screen]::PrimaryScreen
$buffer = [Runtime.InteropServices.Marshal]::AllocHGlobal(220)
try {
    $modes = for ($index = 0; $index -lt 1000; $index++) {
        [Runtime.InteropServices.Marshal]::WriteInt16($buffer,68,220)
        if (-not [CS15DisplayQuery]::EnumDisplaySettings($primary.DeviceName,$index,$buffer)) { break }
        if ([Runtime.InteropServices.Marshal]::ReadInt32($buffer,168) -ne 32) { continue }
        [pscustomobject]@{
            Width = [Runtime.InteropServices.Marshal]::ReadInt32($buffer,172)
            Height = [Runtime.InteropServices.Marshal]::ReadInt32($buffer,176)
        }
    }
    [pscustomobject]@{Width=$primary.Bounds.Width;Height=$primary.Bounds.Height;Modes=@($modes | Sort-Object Width,Height -Unique)}
} finally { [Runtime.InteropServices.Marshal]::FreeHGlobal($buffer) }
