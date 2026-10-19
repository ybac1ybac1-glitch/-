$ErrorActionPreference = "Stop"
$taskName = "AStockStrategyA-V4"
$backend = (Resolve-Path (Join-Path $PSScriptRoot ".")).Path
$project = (Resolve-Path (Join-Path $backend "..")).Path
$pythonw = (Get-Command pythonw.exe -ErrorAction SilentlyContinue).Source
if (-not $pythonw) { $pythonw = (Get-Command python.exe -ErrorAction Stop).Source }
Write-Host "Task: $taskName"
Write-Host "Project: $project"
Write-Host "User: $env:USERDOMAIN\$env:USERNAME"
Write-Host "Action: $pythonw windows_autostart_launcher.pyw"
$answer = Read-Host "Register this task for the current user at logon? Type YES"
if ($answer -ne "YES") { Write-Host "Cancelled"; exit 2 }
$existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
$oldXml = $null
if ($existing) { $oldXml = Export-ScheduledTask -TaskName $taskName }
$action = New-ScheduledTaskAction -Execute $pythonw -Argument "windows_autostart_launcher.pyw" -WorkingDirectory $backend
$trigger = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Days 30)
try {
  Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Description "AStockStrategyA-V4 local Flask and after-close refresh" -Force | Out-Null
} catch {
  if ($oldXml) { Register-ScheduledTask -TaskName $taskName -Xml $oldXml -Force | Out-Null }
  throw
}
Write-Host "Installed. It starts after next logon."
