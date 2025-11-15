# 启动 Flask 服务器（解决中文乱码）
# 使用方法: .\start_server.ps1

# 设置 UTF-8 编码
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"
chcp 65001 | Out-Null

# 激活虚拟环境
& ".\.venv\Scripts\Activate.ps1"

# 启动服务器
Write-Host "正在启动 Flask 服务器..." -ForegroundColor Green
python server\app.py
