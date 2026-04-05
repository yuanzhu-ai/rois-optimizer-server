#!/usr/bin/env python3
"""
调试服务器脚本
"""

import subprocess
import time
import requests
import sys
import threading

def start_server():
    """启动服务器并捕获输出"""
    print("启动服务器...")
    process = subprocess.Popen(
        ["python", "main.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd="D:\\temp\\git\\optimize-server",
        text=True,
        bufsize=1,
        universal_newlines=True
    )
    
    # 启动一个线程来读取服务器输出
    def read_output():
        for line in process.stdout:
            print(f"[SERVER] {line}", end='')
    
    output_thread = threading.Thread(target=read_output)
    output_thread.daemon = True
    output_thread.start()
    
    # 等待服务器启动
    time.sleep(3)
    
    return process

def test_optimize_start():
    """测试启动优化任务"""
    try:
        payload = {
            "airline": "BR",
            "url": "http://localhost",
            "token": "eyJhbGciOiJIUzI1NiJ9.eyIwIjoxLCJpc3MiOiJhZG1pbkBwaS1zb2x1dGlvbiIsImV4cCI6MTc3NTMxNTU4OSwidXNlck5hbWUiOiJ5dWFuLnoifQ.Pk17CJ8Z_alUXwy37UoGoCqabgTK_yOddsr309LdLu8",
            "user": "yuan.z",
            "type": "PO",
            "parameters": {"scenarioId": "3896"}
        }
        
        headers = {
            "X-Airline": "BR",
            "Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.eyIwIjoxLCJpc3MiOiJhZG1pbkBwaS1zb2x1dGlvbiIsImV4cCI6MTc3NTMxNTU4OSwidXNlck5hbWUiOiJ5dWFuLnoifQ.Pk17CJ8Z_alUXwy37UoGoCqabgTK_yOddsr309LdLu8",
            "Content-Type": "application/json"
        }
        
        print("\n发送请求...")
        response = requests.post(
            "http://localhost:8000/api/optimize/start",
            json=payload,
            headers=headers,
            timeout=30
        )
        
        print(f"响应状态码: {response.status_code}")
        print(f"响应内容: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✓ 启动优化任务成功: {result}")
            return result.get("task_id")
        else:
            print(f"✗ 启动优化任务失败: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"✗ 启动优化任务异常: {e}")
        return None

if __name__ == "__main__":
    # 启动服务器
    server_process = start_server()
    
    try:
        # 测试启动优化任务
        print("\n等待5秒后测试...")
        time.sleep(5)
        task_id = test_optimize_start()
        if task_id:
            print(f"\n任务已启动，任务ID: {task_id}")
        else:
            print("\n任务启动失败")
            
    finally:
        # 终止服务器
        print("\n终止服务器...")
        server_process.terminate()
        server_process.wait()
        print("服务器已终止")
