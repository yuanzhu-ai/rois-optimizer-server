#!/usr/bin/env python3
"""
RO优化器测试脚本 - 测试工作目录命名、Live Server URL、认证逻辑
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import json
import time
import subprocess
import threading

BASE_URL = "http://localhost:8000"

# 配置
API_KEY = "your_api_key_here"  # 与config.yaml中配置的api_key一致
LIVE_SERVER_URL = "http://localhost"  # Live Server地址
LIVE_SERVER_TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyIwIjoxLCJpc3MiOiJhZG1pbkBwaS1zb2x1dGlvbiIsImV4cCI6MTc3NTQwMjkyMSwidXNlck5hbWUiOiJ5dWFuLnoifQ.4gyLVMvkbjMncrryw_NaGzoqjh-CBMupZZhSaK_xbm0"

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
    
    def read_output():
        for line in process.stdout:
            print(f"[SERVER] {line}", end='')
    
    output_thread = threading.Thread(target=read_output)
    output_thread.daemon = True
    output_thread.start()
    
    time.sleep(3)
    return process

def test_ro_with_api_key():
    """测试RO优化器 - 使用API Key认证"""
    print("\n" + "="*80)
    print("测试 RO 优化器 - API Key认证 + Live Server调用")
    print("="*80 + "\n")
    
    endpoint = f"{BASE_URL}/api/optimize/start"
    
    payload = {
        "airline": "BR",
        "url": LIVE_SERVER_URL,  # Live Server基础URL
        "token": LIVE_SERVER_TOKEN,  # 用于调用Live Server的token
        "user": "yuan.z",
        "type": "RO",
        "parameters": {"scenarioId": "3739"}
    }
    
    # 使用API Key认证（Header中传入）
    headers = {
        "X-Airline": "BR",
        "X-API-Key": API_KEY,  # optimize-server的认证
        "Content-Type": "application/json"
    }
    
    try:
        print(f"{'='*60}")
        print(f"启动优化任务")
        print(f"{'='*60}")
        print(f"航司: BR")
        print(f"优化器类型: RO")
        print(f"API Key: {API_KEY}")
        print(f"Live Server URL: {LIVE_SERVER_URL}")
        print(f"Live Server Token: {LIVE_SERVER_TOKEN[:20]}...")
        print(f"参数: {json.dumps({'scenarioId': '3739'}, indent=2)}")
        print(f"{'='*60}\n")
        
        # 增加超时时间到20分钟，因为input.gz生成可能需要较长时间
        response = requests.post(endpoint, headers=headers, json=payload, timeout=1200)
        
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

def check_task_status(task_id):
    """查询任务状态"""
    if not task_id:
        return
    
    print(f"\n{'='*60}")
    print(f"查询任务状态: {task_id}")
    print(f"{'='*60}")
    
    headers = {
        "X-Airline": "BR",
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/optimize/status/{task_id}",
            headers=headers,
            timeout=10
        )
        if response.status_code == 200:
            status_data = response.json()
            print(f"任务状态: {status_data.get('status')}")
            if status_data.get('error_message'):
                print(f"错误信息: {status_data.get('error_message')}")
        else:
            print(f"查询失败: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"查询异常: {e}")

if __name__ == "__main__":
    server_process = start_server()
    
    try:
        # 测试RO优化器
        task_id = test_ro_with_api_key()
        if task_id:
            print(f"\n✓ RO任务已启动，任务ID: {task_id}")
            time.sleep(3)
            check_task_status(task_id)
        else:
            print("\n✗ RO任务启动失败")
        
        print("\n" + "="*80)
        print("检查工作目录命名:")
        print("RO目录格式: RO_{scenarioId}_{timestamp}_{taskId}")
        print("="*80)
        
        # 列出工作目录
        workspace_dir = "D:\\temp\\git\\optimize-server\\workspace\\BR"
        if os.path.exists(workspace_dir):
            print(f"\n工作目录内容 ({workspace_dir}):")
            for item in os.listdir(workspace_dir):
                print(f"  - {item}")
        
    finally:
        print("\n终止服务器...")
        server_process.terminate()
        server_process.wait()
        print("服务器已终止")
