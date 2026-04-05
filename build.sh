#!/bin/bash

echo "正在编译优化引擎调度工具..."

# 检查Python是否安装
if ! command -v python3 &> /dev/null; then
    echo "错误：未检测到Python环境，请先安装Python 3.8或更高版本"
    exit 1
fi

# 安装依赖包
echo "正在安装依赖包..."
python3 -m pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "错误：安装依赖包失败"
    exit 1
fi

# 生成 git.properties 文件
echo "正在生成 git.properties 文件..."
python3 generate_git_properties.py
if [ $? -ne 0 ]; then
    echo "警告：生成 git.properties 文件失败，将使用默认值"
fi

echo "编译完成！"
echo "可以使用 start.sh 启动服务"
