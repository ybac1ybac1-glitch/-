$taskName="AStockStrategyA-V4"
$task=Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if($task){Unregister-ScheduledTask -TaskName $taskName -Confirm:$false;Write-Host "Removed $taskName"}else{Write-Host "Task not found"}
