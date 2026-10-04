. "$PSScriptRoot\rcdefs.ps1"
Add-Type @"
using System; using System.Runtime.InteropServices;
public struct RECT { public int L,T,R,B; }
public class W2 { [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
 [DllImport("user32.dll")] public static extern bool SetCursorPos(int x,int y);
 [DllImport("user32.dll")] public static extern void mouse_event(int f,int x,int y,int d,int e); }
"@
$h=[IntPtr]27004894
# Alt tap so SetForegroundWindow is allowed
[W]::keybd_event(0x12,0,0,0); [W]::keybd_event(0x12,0,2,0)
[W]::ShowWindow($h,9)|Out-Null; [W]::SetForegroundWindow($h)|Out-Null; Start-Sleep -Milliseconds 800
$r=New-Object RECT; [W2]::GetWindowRect($h,[ref]$r)|Out-Null; "rect $($r.L) $($r.T) $($r.R) $($r.B)"
$sb=New-Object Text.StringBuilder 256; [void][W]::GetWindowText([W]::GetForegroundWindow(),$sb,256); "fg=$($sb.ToString())"
