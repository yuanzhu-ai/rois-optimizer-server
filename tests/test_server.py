#!/usr/bin/env python3
"""
简单的服务器测试脚本
"""

import subprocess
import time
import requests
import sys

def start_server():
    """启动服务器"""
    print("启动服务器...")
    process = subprocess.Popen(
        ["python", "main.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd="D:\\temp\\git\\optimize-server"
    )
    
    # 等待服务器启动
    time.sleep(3)
    
    return process

def test_health():
    """测试健康检查接口"""
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print(f"✓ 健康检查成功: {response.json()}")
            return True
        else:
            print(f"✗ 健康检查失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ 健康检查异常: {e}")
        return False

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
        
        response = requests.post(
            "http://localhost:8000/api/optimize/start",
            json=payload,
            headers=headers,
            timeout=10
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
        # 测试健康检查
        if test_health():
            # 测试启动优化任务
            task_id = test_optimize_start()
            if task_id:
                print(f"\n任务已启动，任务ID: {task_id}")
        else:
            print("\n服务器未正常运行")
            
    finally:
        # 终止服务器
        print("\n终止服务器...")
        server_process.terminate()
        server_process.wait()
        print("服务器已终止")
