@echo off
echo ====================================
echo  电商内容工厂 Agent - 前端启动
echo ====================================
echo.

cd frontend

echo [1/3] 检查依赖...
if not exist "node_modules\" (
    echo 依赖未安装，开始安装...
    call npm install
    if errorlevel 1 (
        echo 依赖安装失败！
        pause
        exit /b 1
    )
    echo 依赖安装成功！
) else (
    echo 依赖已安装。
)

echo.
echo [2/3] 启动开发服务器...
echo 前端地址: http://localhost:3000
echo 按 Ctrl+C 停止服务器
echo.

call npm run dev

pause
