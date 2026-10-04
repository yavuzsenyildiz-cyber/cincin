Add-Type -AssemblyName UIAutomationClient, UIAutomationTypes
. "$PSScriptRoot\rcdefs.ps1"
$h=[IntPtr]2363648
[W]::ShowWindow($h,9) | Out-Null; [W]::SetForegroundWindow($h) | Out-Null; Start-Sleep -Milliseconds 500
$root=[Windows.Automation.AutomationElement]::FromHandle($h)
$mb=$root.FindFirst([Windows.Automation.TreeScope]::Descendants,(New-Object Windows.Automation.PropertyCondition([Windows.Automation.AutomationElement]::ControlTypeProperty,[Windows.Automation.ControlType]::MenuBar)))
$items=$mb.FindAll([Windows.Automation.TreeScope]::Children,[Windows.Automation.Condition]::TrueCondition)
$items | ForEach-Object { $_.Current.Name }
