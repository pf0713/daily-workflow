# 设置每日14:00自动推文任务 (需管理员权限)
$taskName = "DailyWechatArticle"
$pythonPath = "C:\Users\86151\AppData\Local\Programs\Python\Python312\python.exe"
$scriptPath = "C:\Users\86151\Desktop\CC实验\daily_workflow.py"
$action = New-ScheduledTaskAction -Execute $pythonPath -Argument $scriptPath
$trigger = New-ScheduledTaskTrigger -Daily -At 14:00
$settings = New-ScheduledTaskSettingsSet -WakeToRun -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -RunLevel Highest

# 删除旧任务
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue

# 注册新任务
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force

Write-Host "[OK] 每日推文任务已设置" -ForegroundColor Green
Write-Host "  时间: 每天 14:00"
Write-Host "  脚本: $scriptPath"
Write-Host "  唤醒: 已启用"
Write-Host ""
Write-Host "手动测试运行:"
Write-Host "  schtasks /Run /TN '$taskName'"
Write-Host ""
Write-Host "删除任务:"
Write-Host "  schtasks /Delete /TN '$taskName' /F"
