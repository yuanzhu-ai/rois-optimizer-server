#!/bin/bash
# 在 Linux 构建机上执行：用 PyInstaller 把 main.py 打成单文件可执行
# 产物：dist/optimize_server
#
# 重要：必须在与目标客户机相同 CPU 架构、glibc 版本 ≤ 目标机的 Linux 上构建。
#       建议直接在客户机或同 OS 版本的 Docker 容器内 build。

set -e

cd "$(dirname "$0")"

echo "==> 检查 Python..."
if ! command -v python3 &>/dev/null; then
    echo "错误：未找到 python3"
    exit 1
fi
PYTHON_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "    Python $PYTHON_VER"

echo "==> 准备构建虚拟环境 build-venv ..."
if [ ! -f "build-venv/bin/activate" ]; then
    rm -rf build-venv
    if ! python3 -m venv build-venv; then
        echo "错误：venv 创建失败。Debian/Ubuntu 请安装：sudo apt-get install python${PYTHON_VER}-venv"
        exit 1
    fi
fi
source build-venv/bin/activate

echo "==> 安装依赖 + PyInstaller..."
pip install --upgrade pip -q
pip install -r requirements.txt -q
pip install pyinstaller -q

echo "==> 生成 git.properties ..."
python3 generate_git_properties.py || echo "警告：git.properties 生成失败，使用默认值"

echo "==> 清理旧产物..."
rm -rf build dist

echo "==> PyInstaller 打包 (onefile)..."
pyinstaller --clean optimize_server.spec

if [ ! -f "dist/optimize_server" ]; then
    echo "错误：构建失败，dist/optimize_server 不存在"
    exit 1
fi

SIZE=$(du -h dist/optimize_server | cut -f1)
echo ""
echo "==> 构建完成！"
echo "    可执行文件: $(pwd)/dist/optimize_server ($SIZE)"
echo ""
echo "下一步可以执行 ./deploy.sh pack 将二进制 + 配置 + 运行脚本打成发布包"
