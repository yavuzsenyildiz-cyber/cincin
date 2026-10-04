. "$PSScriptRoot\rcdefs.ps1"
Add-Type -AssemblyName System.Windows.Forms
Add-Type @"
using System; using System.Runtime.InteropServices;
public class W3 { [DllImport("user32.dll")] public static extern bool SetCursorPos(int x,int y);
 [DllImport("user32.dll")] public static extern void mouse_event(int f,int x,int y,int d,int e); }
"@
$h=[IntPtr]27004894
Set-Clipboard -Value 'load "C:/Users/YOGA/AppData/Local/Temp/cincin_terrain/chk.rb"'
[W]::keybd_event(0x12,0,0,0); [W]::keybd_event(0x12,0,2,0)
[W]::ShowWindow($h,9)|Out-Null; [W]::SetForegroundWindow($h)|Out-Null; Start-Sleep -Milliseconds 600
$sb=New-Object Text.StringBuilder 256; [void][W]::GetWindowText([W]::GetForegroundWindow(),$sb,256)
if($sb.ToString() -ne 'Ruby Console'){ "fg wrong: $($sb.ToString())"; exit }
[W3]::SetCursorPos(745,830); [W3]::mouse_event(2,0,0,0,0); [W3]::mouse_event(4,0,0,0,0); Start-Sleep -Milliseconds 300
[System.Windows.Forms.SendKeys]::SendWait('^v'); Start-Sleep -Milliseconds 300
[void][W]::GetWindowText([W]::GetForegroundWindow(),($sb=New-Object Text.StringBuilder 256),256)
if($sb.ToString() -eq 'Ruby Console'){ [System.Windows.Forms.SendKeys]::SendWait('{ENTER}'); "sent" } else { "fg lost: $($sb.ToString())" }
