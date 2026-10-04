. "$PSScriptRoot\rcdefs.ps1"
Add-Type -AssemblyName System.Windows.Forms
$h=[IntPtr]27004894
Set-Clipboard -Value 'load "C:/Users/YOGA/AppData/Local/Temp/cincin_terrain/bahce.rb"'
for($i=0;$i -lt 6;$i++){
  [W]::ShowWindow($h,9)|Out-Null; [W]::SetForegroundWindow($h)|Out-Null; Start-Sleep -Milliseconds 600
  $sb=New-Object Text.StringBuilder 256; [void][W]::GetWindowText([W]::GetForegroundWindow(),$sb,256)
  if($sb.ToString() -eq 'Ruby Console'){ [System.Windows.Forms.SendKeys]::SendWait('^v'); Start-Sleep -Milliseconds 300
    $sb2=New-Object Text.StringBuilder 256; [void][W]::GetWindowText([W]::GetForegroundWindow(),$sb2,256)
    if($sb2.ToString() -eq 'Ruby Console'){ [System.Windows.Forms.SendKeys]::SendWait('{ENTER}'); "sent"; exit } }
  "retry $i fg=$($sb.ToString())"
}
