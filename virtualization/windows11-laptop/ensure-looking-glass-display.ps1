# Run in the signed-in Windows user's session, with the Looking Glass IDD active.
$ErrorActionPreference = 'Stop'
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class LGDisplayLayout {
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
    public struct Device {
        public int cb;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst=32)] public string name;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst=128)] public string description;
        public uint flags;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst=128)] public string id;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst=128)] public string key;
    }
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
    public struct Mode {
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst=32)] public string device;
        public ushort spec, driver, size, extra;
        public uint fields;
        public int x, y;
        public uint orientation, fixedOutput;
        public short color, duplex, yResolution, ttOption, collate;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst=32)] public string form;
        public ushort logPixels;
        public uint bits, width, height, displayFlags, frequency;
        public uint icmMethod, icmIntent, mediaType, ditherType, reserved1, reserved2, panWidth, panHeight;
    }
    [DllImport("user32.dll", CharSet=CharSet.Unicode)]
    public static extern bool EnumDisplayDevices(string device, uint index, ref Device result, uint flags);
    [DllImport("user32.dll", CharSet=CharSet.Unicode)]
    public static extern bool EnumDisplaySettings(string device, int index, ref Mode result);
    [DllImport("user32.dll", CharSet=CharSet.Unicode)]
    public static extern int ChangeDisplaySettingsEx(string device, ref Mode mode, IntPtr window, uint flags, IntPtr param);
    [DllImport("user32.dll", CharSet=CharSet.Unicode, EntryPoint="ChangeDisplaySettingsExW")]
    public static extern int Apply(string device, IntPtr mode, IntPtr window, uint flags, IntPtr param);
    // Keep native null pointers inside C#: PowerShell converts null strings to empty strings.
    public static bool GetDevice(uint index, ref Device result) {
        return EnumDisplayDevices(null, index, ref result, 0);
    }
    public static int ApplySavedLayout() {
        return Apply(null, IntPtr.Zero, IntPtr.Zero, 0, IntPtr.Zero);
    }
}
'@
$displays = @()
for ($i = 0; ; $i++) {
    $device = New-Object LGDisplayLayout+Device
    $device.cb = [Runtime.InteropServices.Marshal]::SizeOf($device)
    if (-not [LGDisplayLayout]::GetDevice($i, [ref]$device)) { break }
    if ($device.flags -band 1) { $displays += $device }
}
$lg = @($displays | Where-Object { $_.description -like '*Looking Glass*' })
if ($lg.Count -ne 1) { throw 'Expected one active Looking Glass display; no display settings were changed.' }
$mode = New-Object LGDisplayLayout+Mode
$mode.size = [Runtime.InteropServices.Marshal]::SizeOf($mode)
if (-not [LGDisplayLayout]::EnumDisplaySettings($lg[0].name, -1, [ref]$mode)) {
    throw 'Could not read the Looking Glass display mode.'
}
$mode.x = 0
$mode.y = 0
# Start from the laptop's usual native mode; the viewer can adapt it for tiling.
$mode.width = 1920
$mode.height = 1200
$mode.frequency = 60
$mode.fields = $mode.fields -bor 0x580020
$result = [LGDisplayLayout]::ChangeDisplaySettingsEx($lg[0].name, [ref]$mode, [IntPtr]::Zero, 0x10000011, [IntPtr]::Zero)
if ($result -ne 0) { throw "Could not make Looking Glass primary: $result" }
foreach ($display in $displays | Where-Object { $_.name -ne $lg[0].name }) {
    $disabled = New-Object LGDisplayLayout+Mode
    $disabled.size = [Runtime.InteropServices.Marshal]::SizeOf($disabled)
    $disabled.fields = 0x180020
    $result = [LGDisplayLayout]::ChangeDisplaySettingsEx($display.name, [ref]$disabled, [IntPtr]::Zero, 0x10000001, [IntPtr]::Zero)
    if ($result -ne 0) { throw "Could not disable $($display.name): $result" }
}
$result = [LGDisplayLayout]::ApplySavedLayout()
if ($result -ne 0) { throw "Could not apply the saved display layout: $result" }
Write-Output "Looking Glass is the sole primary display: $($lg[0].name)"
