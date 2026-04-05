#!/bin/bash

echo "正在启动优化引擎调度工具服务..."

# 检查Python是否安装
if ! command -v python3 &> /dev/null; then
    echo "错误：未检测到Python环境，请先安装Python 3.8或更高版本"
    exit 1
fi

# 检查依赖包是否安装
if ! python3 -m pip list | grep -q fastapi; then
    echo "正在安装依赖包..."
    python3 -m pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "错误：安装依赖包失败"
        exit 1
    fi
fi

# 启动服务
echo "启动服务中..."
uvicorn main:app --host 0.0.0.0 --port 8000
