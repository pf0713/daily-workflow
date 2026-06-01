@echo off
chcp 65001 >nul
echo ============================================
echo   Feishu-Claude Bridge 启动脚本
echo ============================================
echo.

cd /d "C:\Users\86151\Desktop\CC实验"

echo [1/2] 启动 ngrok (将本地 8888 端口暴露到公网)...
start "ngrok" ngrok http 8888

echo [2/2] 启动桥接服务器...
python server.py
pause
