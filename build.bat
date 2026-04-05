@echo off

rem 优化引擎调度工具编译脚本（Windows）

echo 正在编译优化引擎调度工具...

rem 检查Python是否安装
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误：未检测到Python环境，请先安装Python 3.8或更高版本
    pause
    exit /b 1
)

rem 安装依赖包
echo 正在安装依赖包...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo 错误：安装依赖包失败
    pause
    exit /b 1
)

rem 生成 git.properties 文件
echo 正在生成 git.properties 文件...
python generate_git_properties.py
if %errorlevel% neq 0 (
    echo 警告：生成 git.properties 文件失败，将使用默认值
)

echo 编译完成！
echo 可以使用 start.bat 启动服务

pause