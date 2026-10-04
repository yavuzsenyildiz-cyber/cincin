Add-Type -AssemblyName UIAutomationClient, UIAutomationTypes
. "$PSScriptRoot\rcdefs.ps1"
$h=[IntPtr]2363648
[W]::ShowWindow($h,9) | Out-Null; [W]::SetForegroundWindow($h) | Out-Null; Start-Sleep -Milliseconds 500
$A=[Windows.Automation.AutomationElement]; $TS=[Windows.Automation.TreeScope]
function byName($el,$n){ $el.FindFirst($TS::Descendants,(New-Object Windows.Automation.PropertyCondition($A::NameProperty,$n))) }
$root=$A::FromHandle($h)
$ext=byName $root 'Extensions'
$ext.GetCurrentPattern([Windows.Automation.ExpandCollapsePattern]::Pattern).Expand(); Start-Sleep -Milliseconds 700
$desk=$A::RootElement
$dev=byName $desk 'Developer'
"dev: $($dev -ne $null)"
$dev.GetCurrentPattern([Windows.Automation.ExpandCollapsePattern]::Pattern).Expand(); Start-Sleep -Milliseconds 700
$rc=byName $desk 'Ruby Console'
"rc: $($rc -ne $null)"
$rc.GetCurrentPattern([Windows.Automation.InvokePattern]::Pattern).Invoke()
