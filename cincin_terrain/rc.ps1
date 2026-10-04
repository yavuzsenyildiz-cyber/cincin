Add-Type @"
using System; using System.Text; using System.Runtime.InteropServices;
public class W {
 public delegate bool EP(IntPtr h, IntPtr l);
 [DllImport("user32.dll")] public static extern bool EnumWindows(EP f, IntPtr l);
 [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
 [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
 [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
 [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c);
 [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
 [DllImport("user32.dll")] public static extern void keybd_event(byte k, byte s, int f, int e);
}
"@
$found = @()
[W]::EnumWindows({ param($h,$l) $sb=New-Object Text.StringBuilder 256; [void][W]::GetWindowText($h,$sb,256); if([W]::IsWindowVisible($h) -and $sb.ToString() -match 'Ruby Console|SketchUp'){ $script:found += ,@($h,$sb.ToString()) }; $true }, [IntPtr]::Zero) | Out-Null
$found | ForEach-Object { "$($_[0]) | $($_[1])" }
