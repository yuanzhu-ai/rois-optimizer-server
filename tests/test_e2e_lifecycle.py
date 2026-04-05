"""
端到端生命周期测试 — 通过 FastAPI TestClient 测试完整流程

覆盖:
- 6 种优化器类型的完整 start → status → progress → complete 流程
- input.gz 获取 + 优化器执行 + output.gz 回传 + 文件归档 全链路
- 任务停止流程
- 并发任务
- 任务列表查询
"""
import gzip
import json
import os
import time

import pytest


# ============================================================
# 辅助函数
# ============================================================

def _start_task(client, airline, opt_type, params, live_server_url, token="test_token"):
    """通过 API 启动任务并返回 task_id"""
    payload = {
        "airline": airline,
        "type": opt_type,
        "parameters": params,
        "url": live_server_url,
        "token": token,
        "user": "test_user",
    }
    resp = client.post(
        "/api/optimize/start",
        json=payload,
        headers={"X-Airline": airline},
    )
    return resp


def _wait_for_task_completion(client, task_id, airline, timeout=15):
    """等待任务完成，返回最终状态"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = client.get(
            f"/api/optimize/status/{task_id}",
            headers={"X-Airline": airline},
        )
        data = resp.json()
        if data['status'] in ('completed', 'failed', 'stopped'):
            return data
        time.sleep(0.3)
    raise TimeoutError(f"Task {task_id} did not complete within {timeout}s, last status: {data['status']}")


# ============================================================
# PO 端到端测试
# ============================================================

class TestPOEndToEnd:
    """PO 优化器完整生命周期"""

    @pytest.mark.parametrize("airline", ["BR", "F8"])
    def test_po_full_lifecycle(self, api_client, test_config, airline):
        """PO: start → running → progress → completed，验证 input/output 全链路"""
        resp = _start_task(
            api_client, airline, "PO",
            {"scenarioId": "3896"},
            test_config['live_server_url'],
        )
        assert resp.status_code == 200
        task_id = resp.json()['task_id']
        assert resp.json()['status'] == 'started'

        # 等待任务完成
        final = _wait_for_task_completion(api_client, task_id, airline)
        assert final['status'] == 'completed'
        assert final['error_message'] is None

        # 验证进度到达 100
        progress_resp = api_client.get(
            f"/api/optimize/progress/{task_id}",
            headers={"X-Airline": airline},
        )
        assert progress_resp.json()['progress'] == 100

        # 验证 Mock Server 收到了 input 和 output 请求
        requests = test_config['mock_requests']
        input_reqs = [r for r in requests if '/comptxt' in r['path']]
        output_reqs = [r for r in requests if '/solution' in r['path']]
        assert len(input_reqs) >= 1, "应该有 input 请求"
        assert len(output_reqs) >= 1, "应该有 output 请求"


# ============================================================
# RO 端到端测试
# ============================================================

class TestROEndToEnd:
    """RO 优化器完整生命周期"""

    @pytest.mark.parametrize("airline", ["BR", "F8"])
    def test_ro_full_lifecycle(self, api_client, test_config, airline):
        """RO: 完整生命周期"""
        resp = _start_task(
            api_client, airline, "RO",
            {"scenarioId": "5432"},
            test_config['live_server_url'],
        )
        assert resp.status_code == 200
        task_id = resp.json()['task_id']

        final = _wait_for_task_completion(api_client, task_id, airline)
        assert final['status'] == 'completed'

        # 验证 RO 对应的端点被调用
        input_reqs = [r for r in test_config['mock_requests'] if '/ro/comptxt' in r['path']]
        output_reqs = [r for r in test_config['mock_requests'] if '/ro/solution' in r['path']]
        assert len(input_reqs) >= 1
        assert len(output_reqs) >= 1


# ============================================================
# TO 端到端测试
# ============================================================

class TestTOEndToEnd:
    """TO 优化器完整生命周期"""

    def test_to_full_lifecycle(self, api_client, test_config):
        """TO: 完整生命周期"""
        resp = _start_task(
            api_client, "BR", "TO",
            {"scenarioId": "9999"},
            test_config['live_server_url'],
        )
        assert resp.status_code == 200
        task_id = resp.json()['task_id']

        final = _wait_for_task_completion(api_client, task_id, "BR")
        assert final['status'] == 'completed'


# ============================================================
# Rule/change_flight 端到端测试
# ============================================================

class TestRuleChangeFlightEndToEnd:
    """Rule/change_flight 完整生命周期"""

    @pytest.mark.parametrize("airline", ["BR", "F8"])
    def test_change_flight_full_lifecycle(self, api_client, test_config, airline):
        """Rule/change_flight: start → completed，验证 JSON 请求体"""
        params = {
            "category": "change_flight",
            "airline": airline,
            "division": "P",
            "fltId": "162906,162218,162905",
        }
        resp = _start_task(
            api_client, airline, "Rule", params,
            test_config['live_server_url'],
        )
        assert resp.status_code == 200
        task_id = resp.json()['task_id']

        final = _wait_for_task_completion(api_client, task_id, airline)
        assert final['status'] == 'completed'

        # 验证 change_flight 端点被调用
        input_reqs = [r for r in test_config['mock_requests'] if '/byFlight/comptxt' in r['path']]
        assert len(input_reqs) >= 1

        # 验证请求体格式
        body = json.loads(input_reqs[0]['body_text'])
        assert body['flightIds'] == [162906, 162218, 162905]


# ============================================================
# Rule/manday 端到端测试
# ============================================================

class TestRuleMandayEndToEnd:
    """Rule/manday 完整生命周期"""

    @pytest.mark.parametrize("airline", ["BR", "F8"])
    def test_manday_full_lifecycle(self, api_client, test_config, airline):
        """Rule/manday: start → completed"""
        params = {
            "category": "manday",
            "startDt": "2025-02-01",
            "endDt": "2025-03-30",
            "division": "P",
        }
        resp = _start_task(
            api_client, airline, "Rule", params,
            test_config['live_server_url'],
        )
        assert resp.status_code == 200
        task_id = resp.json()['task_id']

        final = _wait_for_task_completion(api_client, task_id, airline)
        assert final['status'] == 'completed'

        input_reqs = [r for r in test_config['mock_requests'] if '/ro/partial/comptxt' in r['path']]
        assert len(input_reqs) >= 1


# ============================================================
# Rule/manday_byCrew 端到端测试
# ============================================================

class TestRuleMandayByCrewEndToEnd:
    """Rule/manday_byCrew 完整生命周期"""

    @pytest.mark.parametrize("airline", ["BR", "F8"])
    def test_manday_byCrew_full_lifecycle(self, api_client, test_config, airline):
        """Rule/manday_byCrew: start → completed"""
        params = {
            "category": "manday_byCrew",
            "startDt": "2024-09-12",
            "endDt": "2024-09-30",
            "division": "P",
            "crewIds": "I73313,H47887,I73647",
        }
        resp = _start_task(
            api_client, airline, "Rule", params,
            test_config['live_server_url'],
        )
        assert resp.status_code == 200
        task_id = resp.json()['task_id']

        final = _wait_for_task_completion(api_client, task_id, airline)
        assert final['status'] == 'completed'

        input_reqs = [r for r in test_config['mock_requests'] if '/byCrew/comptxt' in r['path']]
        assert len(input_reqs) >= 1

        body = json.loads(input_reqs[0]['body_text'])
        assert body['crewIds'] == ['I73313', 'H47887', 'I73647']


# ============================================================
# 任务停止测试
# ============================================================

class TestTaskStop:
    """任务停止流程"""

    def test_stop_running_task(self, api_client, test_config):
        """停止一个正在运行的任务"""
        resp = _start_task(
            api_client, "BR", "PO",
            {"scenarioId": "1111"},
            test_config['live_server_url'],
        )
        assert resp.status_code == 200
        task_id = resp.json()['task_id']

        # 稍等确保任务开始运行
        time.sleep(0.2)

        # 停止任务
        stop_resp = api_client.post(
            f"/api/optimize/stop/{task_id}",
            headers={"X-Airline": "BR"},
        )
        assert stop_resp.status_code == 200
        assert stop_resp.json()['status'] == 'stopped'

        # 确认状态为 stopped
        status_resp = api_client.get(
            f"/api/optimize/status/{task_id}",
            headers={"X-Airline": "BR"},
        )
        assert status_resp.json()['status'] == 'stopped'


# ============================================================
# 任务列表查询测试
# ============================================================

class TestTaskQueries:
    """任务列表和状态查询"""

    def test_system_info(self, api_client, test_config):
        """系统信息接口"""
        resp = api_client.get(
            "/api/system/info",
            headers={"X-Airline": "BR"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data['service'] == '优化引擎调度工具'
        assert data['status'] == 'running'

    def test_optimizer_list(self, api_client, test_config):
        """获取优化器列表"""
        resp = api_client.get(
            "/api/optimizers",
            headers={"X-Airline": "BR"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert set(data['optimizers']) == {'PO', 'RO', 'TO', 'Rule'}

    def test_running_tasks_list(self, api_client, test_config):
        """获取运行中任务列表"""
        resp = api_client.get(
            "/api/tasks/running",
            headers={"X-Airline": "BR"},
        )
        assert resp.status_code == 200
        assert isinstance(resp.json()['tasks'], list)

    def test_all_tasks_list(self, api_client, test_config):
        """获取所有任务列表"""
        # 先启动一个任务
        start_resp = _start_task(
            api_client, "BR", "PO",
            {"scenarioId": "2222"},
            test_config['live_server_url'],
        )
        task_id = start_resp.json()['task_id']

        # 查询所有任务
        resp = api_client.get(
            "/api/tasks/all",
            headers={"X-Airline": "BR"},
        )
        assert resp.status_code == 200
        tasks = resp.json()['tasks']
        task_ids = [t['task_id'] for t in tasks]
        assert task_id in task_ids

    def test_task_not_found(self, api_client, test_config):
        """查询不存在的任务返回 404"""
        resp = api_client.get(
            "/api/optimize/status/nonexistent-task-id",
            headers={"X-Airline": "BR"},
        )
        assert resp.status_code == 404


# ============================================================
# 并发任务测试
# ============================================================

class TestConcurrentTasks:
    """并发任务测试"""

    def test_multiple_tasks_different_types(self, api_client, test_config):
        """同时启动多种类型的任务"""
        tasks = []

        # 启动 PO
        resp = _start_task(api_client, "BR", "PO", {"scenarioId": "1001"}, test_config['live_server_url'])
        assert resp.status_code == 200
        tasks.append(("BR", resp.json()['task_id']))

        # 启动 RO
        resp = _start_task(api_client, "F8", "RO", {"scenarioId": "1002"}, test_config['live_server_url'])
        assert resp.status_code == 200
        tasks.append(("F8", resp.json()['task_id']))

        # 启动 Rule/change_flight
        resp = _start_task(
            api_client, "BR", "Rule",
            {"category": "change_flight", "airline": "BR", "division": "P", "fltId": "100"},
            test_config['live_server_url'],
        )
        assert resp.status_code == 200
        tasks.append(("BR", resp.json()['task_id']))

        # 等待全部完成
        for airline, task_id in tasks:
            final = _wait_for_task_completion(api_client, task_id, airline)
            assert final['status'] == 'completed', f"Task {task_id} failed: {final.get('error_message')}"

    def test_multiple_tasks_same_airline(self, api_client, test_config):
        """同一航司同时启动多个任务"""
        task_ids = []
        for i in range(3):
            resp = _start_task(
                api_client, "BR", "PO",
                {"scenarioId": str(2000 + i)},
                test_config['live_server_url'],
            )
            assert resp.status_code == 200
            task_ids.append(resp.json()['task_id'])

        for task_id in task_ids:
            final = _wait_for_task_completion(api_client, task_id, "BR")
            assert final['status'] == 'completed'
