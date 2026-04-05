#!/usr/bin/env python3
"""
Optimize Server API 测试脚本（自动启动服务器）
"""

import requests
import json
import sys
import time
import subprocess
import threading

BASE_URL = "http://localhost:8000"

def start_server():
    """启动服务器"""
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

def test_po():
    """测试 PO 优化器 - 获取input.gz"""
    print("\n" + "="*80)
    print("测试 PO 优化器 - 从Live Server获取input.gz")
    print("="*80 + "\n")
    
    endpoint = f"{BASE_URL}/api/optimize/start"
    
    # 配置真实的Live Server地址和参数
    # 注意：请根据实际环境修改Live Server地址
    LIVE_SERVER_URL = "http://192.168.199.182"  # 请替换为真实的Live Server地址
    TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyIwIjoxLCJpc3MiOiJhZG1pbkBwaS1zb2x1dGlvbiIsImV4cCI6MTc3NTMxNTU4OSwidXNlck5hbWUiOiJ5dWFuLnoifQ.Pk17CJ8Z_alUXwy37UoGoCqabgTK_yOddsr309LdLu8"
    
    payload = {
        "airline": "BR",
        "url": LIVE_SERVER_URL,  # Live Server基础URL
        "token": TOKEN,
        "user": "yuan.z",
        "type": "PO",
        "parameters": {"scenarioId": "3896"}
    }
    
    headers = {
        "X-Airline": "BR",
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
    
    try:
        print(f"{'='*60}")
        print(f"启动优化任务")
        print(f"{'='*60}")
        print(f"航司: BR")
        print(f"优化器类型: PO")
        print(f"Live Server: {LIVE_SERVER_URL}")
        print(f"参数: {json.dumps({'scenarioId': '3896'}, indent=2)}")
        print(f"{'='*60}\n")
        
        response = requests.post(endpoint, headers=headers, json=payload, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✓ 请求成功!")
            print(f"响应: {json.dumps(result, indent=2)}")
            return result.get("task_id")
        else:
            print(f"✗ 请求失败! 状态码: {response.status_code}")
            print(f"响应: {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"✗ 请求异常: {e}")
        return None

if __name__ == "__main__":
    # 启动服务器
    server_process = start_server()
    
    # 配置请求头（用于状态查询）
    TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyIwIjoxLCJpc3MiOiJhZG1pbkBwaS1zb2x1dGlvbiIsImV4cCI6MTc3NTMxNTU4OSwidXNlck5hbWUiOiJ5dWFuLnoifQ.Pk17CJ8Z_alUXwy37UoGoCqabgTK_yOddsr309LdLu8"
    status_headers = {
        "X-Airline": "BR",
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
    
    try:
        # 测试 PO 优化器
        task_id = test_po()
        if task_id:
            print(f"\n✓ 任务已启动，任务ID: {task_id}")
            print("\n任务正在执行，请查看服务器输出以获取input.gz获取状态...")
            
            # 等待几秒让任务有时间获取input.gz
            import time
            time.sleep(5)
            
            # 查询任务状态
            status_endpoint = f"{BASE_URL}/api/optimize/status/{task_id}"
            try:
                status_response = requests.get(status_endpoint, headers=status_headers, timeout=10)
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    print(f"\n任务状态: {status_data.get('status')}")
                    if status_data.get('error_message'):
                        print(f"错误信息: {status_data.get('error_message')}")
            except Exception as e:
                print(f"查询状态失败: {e}")
        else:
            print("\n✗ 任务启动失败")
            
    finally:
        # 终止服务器
        print("\n终止服务器...")
        server_process.terminate()
        server_process.wait()
        print("服务器已终止")
