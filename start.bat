@echo off

rem 优化引擎调度工具启动脚本（Windows）

echo 正在启动优化引擎调度工具服务...

rem 检查Python是否安装
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误：未检测到Python环境，请先安装Python 3.8或更高版本
    pause
    exit /b 1
)

rem 检查依赖包是否安装
pip list | findstr "fastapi" >nul 2>&1
if %errorlevel% neq 0 (
    echo 正在安装依赖包...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo 错误：安装依赖包失败
        pause
        exit /b 1
    )
)

rem 启动服务
echo 启动服务中...
uvicorn main:app --host 0.0.0.0 --port 8000

pause
