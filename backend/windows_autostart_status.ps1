$taskName="AStockStrategyA-V4"
$task=Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if(-not $task){Write-Host "NOT_INSTALLED";exit 1}
Write-Host ("STATE="+$task.State)
Write-Host ("TASK="+$task.TaskName)
Get-Process pythonw,python -ErrorAction SilentlyContinue | Select-Object Id,ProcessName,Path
