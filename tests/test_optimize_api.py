#!/usr/bin/env python3
"""
Optimize Server API 测试脚本
用于测试启动优化任务、查询任务状态等功能
"""

import requests
import json
import sys
import time
import argparse

BASE_URL = "http://localhost:8000"

def start_optimization(airline, url, token, user, optimizer_type, parameters):
    """
    启动优化任务

    Args:
        airline: 航司二字码
        url: Live Server地址
        token: 认证Token
        user: 用户ID
        optimizer_type: 优化器类型（PO, RO, TO, Rule）
        parameters: 优化参数

    Returns:
        task_id: 任务ID
    """
    endpoint = f"{BASE_URL}/api/optimize/start"

    payload = {
        "airline": airline,
        "url": url,
        "token": token,
        "user": user,
        "type": optimizer_type,
        "parameters": parameters
    }

    headers = {
        "X-Airline": airline,
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    try:
        print(f"\n{'='*60}")
        print(f"启动优化任务")
        print(f"{'='*60}")
        print(f"航司: {airline}")
        print(f"优化器类型: {optimizer_type}")
        print(f"参数: {json.dumps(parameters, indent=2)}")
        print(f"{'='*60}\n")

        response = requests.post(endpoint, headers=headers, json=payload, timeout=30)

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


def get_task_status(airline, token, task_id):
    """
    查询任务状态

    Args:
        airline: 航司二字码
        token: 认证Token
        task_id: 任务ID

    Returns:
        任务状态信息
    """
    endpoint = f"{BASE_URL}/api/optimize/status/{task_id}"

    headers = {
        "X-Airline": airline,
        "Authorization": f"Bearer {token}"
    }

    try:
        print(f"\n{'='*60}")
        print(f"查询任务状态")
        print(f"{'='*60}")
        print(f"航司: {airline}")
        print(f"任务ID: {task_id}")
        print(f"{'='*60}\n")

        response = requests.get(endpoint, headers=headers, timeout=30)

        if response.status_code == 200:
            result = response.json()
            print(f"✓ 请求成功!")
            print(f"响应: {json.dumps(result, indent=2)}")
            return result
        else:
            print(f"✗ 请求失败! 状态码: {response.status_code}")
            print(f"响应: {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"✗ 请求异常: {e}")
        return None


def get_task_progress(airline, token, task_id):
    """
    查询任务进度

    Args:
        airline: 航司二字码
        token: 认证Token
        task_id: 任务ID

    Returns:
        任务进度信息
    """
    endpoint = f"{BASE_URL}/api/optimize/progress/{task_id}"

    headers = {
        "X-Airline": airline,
        "Authorization": f"Bearer {token}"
    }

    try:
        print(f"\n{'='*60}")
        print(f"查询任务进度")
        print(f"{'='*60}")
        print(f"航司: {airline}")
        print(f"任务ID: {task_id}")
        print(f"{'='*60}\n")

        response = requests.get(endpoint, headers=headers, timeout=30)

        if response.status_code == 200:
            result = response.json()
            print(f"✓ 请求成功!")
            print(f"响应: {json.dumps(result, indent=2)}")
            return result
        else:
            print(f"✗ 请求失败! 状态码: {response.status_code}")
            print(f"响应: {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"✗ 请求异常: {e}")
        return None


def stop_task(airline, token, task_id):
    """
    停止任务

    Args:
        airline: 航司二字码
        token: 认证Token
        task_id: 任务ID

    Returns:
        停止结果
    """
    endpoint = f"{BASE_URL}/api/optimize/stop/{task_id}"

    headers = {
        "X-Airline": airline,
        "Authorization": f"Bearer {token}"
    }

    try:
        print(f"\n{'='*60}")
        print(f"停止任务")
        print(f"{'='*60}")
        print(f"航司: {airline}")
        print(f"任务ID: {task_id}")
        print(f"{'='*60}\n")

        response = requests.post(endpoint, headers=headers, timeout=30)

        if response.status_code == 200:
            result = response.json()
            print(f"✓ 请求成功!")
            print(f"响应: {json.dumps(result, indent=2)}")
            return result
        else:
            print(f"✗ 请求失败! 状态码: {response.status_code}")
            print(f"响应: {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"✗ 请求异常: {e}")
        return None


def monitor_task(airline, token, task_id, interval=2, max_iterations=30):
    """
    监控任务直到完成

    Args:
        airline: 航司二字码
        token: 认证Token
        task_id: 任务ID
        interval: 查询间隔（秒）
        max_iterations: 最大查询次数
    """
    print(f"\n开始监控任务: {task_id}")
    print(f"查询间隔: {interval}秒")
    print(f"最大查询次数: {max_iterations}\n")

    for i in range(max_iterations):
        status = get_task_status(airline, token, task_id)

        if status:
            task_status = status.get("status")
            progress = status.get("progress", 0)

            print(f"[{i+1}/{max_iterations}] 状态: {task_status}, 进度: {progress}%")

            if task_status in ["completed", "failed", "cancelled"]:
                print(f"\n任务已结束，最终状态: {task_status}")
                return task_status

        time.sleep(interval)

    print(f"\n达到最大查询次数，任务仍在运行中")
    return None


def test_po():
    """测试 PO 优化器"""
    print("\n" + "="*80)
    print("测试 PO 优化器")
    print("="*80 + "\n")

    return start_optimization(
        airline="BR",
        url="http://localhost",
        token="eyJhbGciOiJIUzI1NiJ9.eyIwIjoxLCJpc3MiOiJhZG1pbkBwaS1zb2x1dGlvbiIsImV4cCI6MTc3NTMxNTU4OSwidXNlck5hbWUiOiJ5dWFuLnoifQ.Pk17CJ8Z_alUXwy37UoGoCqabgTK_yOddsr309LdLu8",
        user="yuan.z",
        optimizer_type="PO",
        parameters={"scenarioId": "3896"}
    )


def test_ro():
    """测试 RO 优化器"""
    print("\n" + "="*80)
    print("测试 RO 优化器")
    print("="*80 + "\n")

    return start_optimization(
        airline="F8",
        url="http://localhost",
        token="eyJhbGciOiJIUzI1NiJ9.eyIwIjoxLCJpc3MiOiJhZG1pbkBwaS1zb2x1dGlvbiIsImV4cCI6MTc3NTMxNTU4OSwidXNlck5hbWUiOiJ5dWFuLnoifQ.Pk17CJ8Z_alUXwy37UoGoCqabgTK_yOddsr309LdLu8",
        user="yuan.z",
        optimizer_type="RO",
        parameters={"scenarioId": "345"}
    )


def test_rule_change_flight():
    """测试 Rule 优化器 (change_flight)"""
    print("\n" + "="*80)
    print("测试 Rule 优化器 (change_flight)")
    print("="*80 + "\n")

    return start_optimization(
        airline="BR",
        url="http://localhost",
        token="eyJhbGciOiJIUzI1NiJ9.eyIwIjoxLCJpc3MiOiJhZG1pbkBwaS1zb2x1dGlvbiIsImV4cCI6MTc3NTMxNTU4OSwidXNlck5hbWUiOiJ5dWFuLnoifQ.Pk17CJ8Z_alUXwy37UoGoCqabgTK_yOddsr309LdLu8",
        user="yuan.z",
        optimizer_type="Rule",
        parameters={
            "category": "change_flight",
            "scenarioId": "0",
            "airline": "BR",
            "fltId": "1,2,3,4,5,6,7",
            "division": "P"
        }
    )


def test_rule_manday():
    """测试 Rule 优化器 (manday)"""
    print("\n" + "="*80)
    print("测试 Rule 优化器 (manday)")
    print("="*80 + "\n")

    return start_optimization(
        airline="BR",
        url="http://localhost",
        token="eyJhbGciOiJIUzI1NiJ9.eyIwIjoxLCJpc3MiOiJhZG1pbkBwaS1zb2x1dGlvbiIsImV4cCI6MTc3NTMxNTU4OSwidXNlck5hbWUiOiJ5dWFuLnoifQ.Pk17CJ8Z_alUXwy37UoGoCqabgTK_yOddsr309LdLu8",
        user="yuan.z",
        optimizer_type="Rule",
        parameters={
            "category": "manday",
            "scenarioId": "0",
            "startDt": "2024-01-01",
            "endDt": "2024-08-31",
            "division": "P"
        }
    )


def test_rule_manday_bycrew():
    """测试 Rule 优化器 (manday_byCrew)"""
    print("\n" + "="*80)
    print("测试 Rule 优化器 (manday_byCrew)")
    print("="*80 + "\n")

    return start_optimization(
        airline="BR",
        url="http://localhost",
        token="eyJhbGciOiJIUzI1NiJ9.eyIwIjoxLCJpc3MiOiJhZG1pbkBwaS1zb2x1dGlvbiIsImV4cCI6MTc3NTMxNTU4OSwidXNlck5hbWUiOiJ5dWFuLnoifQ.Pk17CJ8Z_alUXwy37UoGoCqabgTK_yOddsr309LdLu8",
        user="yuan.z",
        optimizer_type="Rule",
        parameters={
            "category": "manday_byCrew",
            "scenarioId": "0",
            "crewIds": "I73313,H47887,I73647,E53500",
            "startDt": "2024-01-01",
            "endDt": "2024-08-31",
            "division": "P"
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Optimize Server API 测试工具")
    parser.add_argument("--type", "-t", choices=["po", "ro", "rule-cf", "rule-md", "rule-mdc", "monitor", "status", "progress", "stop"],
                        default="po", help="测试类型")
    parser.add_argument("--airline", "-a", default="BR", help="航司二字码")
    parser.add_argument("--token", default="eyJhbGciOiJIUzI1NiJ9.eyIwIjoxLCJpc3MiOiJhZG1pbkBwaS1zb2x1dGlvbiIsImV4cCI6MTc3NTMxNTU4OSwidXNlck5hbWUiOiJ5dWFuLnoifQ.Pk17CJ8Z_alUXwy37UoGoCqabgTK_yOddsr309LdLu8",
                        help="认证Token")
    parser.add_argument("--user", "-u", default="yuan.z", help="用户ID")
    parser.add_argument("--task-id", help="任务ID (用于monitor/status/progress/stop)")
    parser.add_argument("--interval", "-i", type=int, default=2, help="监控查询间隔（秒）")
    parser.add_argument("--max-iterations", "-m", type=int, default=30, help="最大查询次数")

    args = parser.parse_args()

    TOKEN = args.token

    if args.type == "po":
        task_id = test_po()
        if task_id:
            print(f"\n任务已启动，任务ID: {task_id}")
            response = input("\n是否立即监控任务? (y/n): ")
            if response.lower() == 'y':
                monitor_task(args.airline, TOKEN, task_id, args.interval, args.max_iterations)

    elif args.type == "ro":
        task_id = test_ro()
        if task_id:
            print(f"\n任务已启动，任务ID: {task_id}")

    elif args.type == "rule-cf":
        task_id = test_rule_change_flight()
        if task_id:
            print(f"\n任务已启动，任务ID: {task_id}")

    elif args.type == "rule-md":
        task_id = test_rule_manday()
        if task_id:
            print(f"\n任务已启动，任务ID: {task_id}")

    elif args.type == "rule-mdc":
        task_id = test_rule_manday_bycrew()
        if task_id:
            print(f"\n任务已启动，任务ID: {task_id}")

    elif args.type == "monitor":
        if not args.task_id:
            print("✗ 错误: monitor模式需要提供 --task-id 参数")
            sys.exit(1)
        monitor_task(args.airline, TOKEN, args.task_id, args.interval, args.max_iterations)

    elif args.type == "status":
        if not args.task_id:
            print("✗ 错误: status模式需要提供 --task-id 参数")
            sys.exit(1)
        get_task_status(args.airline, TOKEN, args.task_id)

    elif args.type == "progress":
        if not args.task_id:
            print("✗ 错误: progress模式需要提供 --task-id 参数")
            sys.exit(1)
        get_task_progress(args.airline, TOKEN, args.task_id)

    elif args.type == "stop":
        if not args.task_id:
            print("✗ 错误: stop模式需要提供 --task-id 参数")
            sys.exit(1)
        stop_task(args.airline, TOKEN, args.task_id)
