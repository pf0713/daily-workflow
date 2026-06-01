@echo off
chcp 65001 >nul
echo === 设置每日14:00自动推文任务 ===
echo.

set TASK_NAME=DailyWechatArticle
set SCRIPT_DIR=C:\Users\86151\Desktop\CC实验
set PYTHON_PATH=C:\Users\86151\AppData\Local\Programs\Python\Python312\python.exe

echo 任务名称: %TASK_NAME%
echo 脚本目录: %SCRIPT_DIR%
echo Python路径: %PYTHON_PATH%
echo.

REM 先删除旧任务（如果存在）
schtasks /Delete /TN "%TASK_NAME%" /F 2>nul

REM 创建新任务
REM /SC DAILY: 每天
REM /ST 14:00: 下午2点
REM /WAKE: 唤醒电脑执行
REM /RL HIGHEST: 最高权限运行
schtasks /Create ^
  /TN "%TASK_NAME%" ^
  /TR "%PYTHON_PATH% %SCRIPT_DIR%\daily_workflow.py" ^
  /SC DAILY ^
  /ST 14:00 ^
  /WAKE ^
  /RL HIGHEST ^
  /F

echo.
if %ERRORLEVEL% EQU 0 (
  echo [成功] 每日推文任务已设置
  echo.
  echo 任务详情:
  echo   时间: 每天 14:00
  echo   脚本: %SCRIPT_DIR%\daily_workflow.py
  echo   唤醒: 已启用（睡眠中也会唤醒执行）
  echo.
  echo 你可以通过以下命令管理:
  echo   查看: schtasks /Query /TN "%TASK_NAME%"
  echo   运行: schtasks /Run /TN "%TASK_NAME%"
  echo   删除: schtasks /Delete /TN "%TASK_NAME%" /F
) else (
  echo [失败] 请以管理员身份运行此脚本
  echo   右键 setup_scheduler.bat → 以管理员身份运行
)

pause
