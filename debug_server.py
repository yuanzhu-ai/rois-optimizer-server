#!/usr/bin/env python3
"""
调试服务器脚本

使用方法:
    设置环境变量后运行:
    export ROIS_TEST_TOKEN=your_test_token
    export ROIS_API_KEY=your_api_key
    python debug_server.py
"""

import os
import subprocess
import time
import requests
import threading

# 从环境变量读取敏感配置
TEST_TOKEN = os.environ.get("ROIS_TEST_TOKEN", "test_token_placeholder")
TEST_API_KEY = os.environ.get("ROIS_API_KEY", "your_api_key_here")
SERVER_URL = os.environ.get("ROIS_SERVER_URL", "http://localhost:8000")
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))


def start_server():
    """启动服务器并捕获输出"""
    print("启动服务器...")
    process = subprocess.Popen(
        ["python", "main.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=PROJECT_DIR,
        text=True,
        bufsize=1,
        universal_newlines=True
    )

    def read_output():
        for line in process.stdout:
            print(f"[SERVER] {line}", end='')

    output_thread = threading.Thread(target=read_output)
    output_thread.daemon = True
    output_thread.start()

    time.sleep(3)
    return process


def test_optimize_start():
    """测试启动优化任务"""
    try:
        payload = {
            "airline": "BR",
            "url": "http://localhost",
            "token": TEST_TOKEN,
            "user": "debug_user",
            "type": "PO",
            "parameters": {"scenarioId": "3896"}
        }

        headers = {
            "X-Airline": "BR",
            "X-API-Key": TEST_API_KEY,
            "Content-Type": "application/json"
        }

        print("\n发送请求...")
        response = requests.post(
            f"{SERVER_URL}/api/optimize/start",
            json=payload,
            headers=headers,
            timeout=30
        )

        print(f"响应状态码: {response.status_code}")
        print(f"响应内容: {response.text}")

        if response.status_code == 200:
            result = response.json()
            print(f"启动优化任务成功: {result}")
            return result.get("task_id")
        else:
            print(f"启动优化任务失败: {response.status_code}")
            return None

    except Exception as e:
        print(f"启动优化任务异常: {e}")
        return None


if __name__ == "__main__":
    server_process = start_server()

    try:
        print("\n等待5秒后测试...")
        time.sleep(5)
        task_id = test_optimize_start()
        if task_id:
            print(f"\n任务已启动，任务ID: {task_id}")
        else:
            print("\n任务启动失败")

    finally:
        print("\n终止服务器...")
        server_process.terminate()
        server_process.wait()
        print("服务器已终止")
