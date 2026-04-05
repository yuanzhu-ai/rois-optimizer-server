"""
Input 接口测试 — 测试从 Live Server 获取 input.gz

覆盖所有 6 种优化器类型 × 2 个航司:
- PO (BR, F8)
- RO (BR, F8)
- TO (BR, F8)
- Rule/change_flight (BR, F8)
- Rule/manday (BR, F8)
- Rule/manday_byCrew (BR, F8)

验证:
- HTTP 请求正确发送到 Mock Live Server
- 请求 URL 正确
- 请求 body 格式正确
- input.gz 文件正确保存到工作目录
"""
import gzip
import json
import os
import time

import pytest


class TestPOInput:
    """PO 优化器 input.gz 获取测试"""

    @pytest.mark.parametrize("airline", ["BR", "F8"])
    def test_po_input_fetch_success(self, test_config, airline):
        """PO: 成功获取 input.gz，验证请求格式和文件保存"""
        from src.tasks.task_manager import Task

        task = Task(
            task_id="test-po-input-001",
            airline=airline,
            optimizer_type="PO",
            parameters={"scenarioId": "3896"},
            url=test_config['live_server_url'],
            token="test_token",
        )

        result = task._fetch_input_data()
        assert result is True

        # 验证 input.gz 文件已保存
        assert task.input_file_path is not None
        assert os.path.exists(task.input_file_path)
        assert task.input_file_path.endswith("input.gz")

        # 验证文件内容 (requests 库自动解压 gzip，保存的可能是明文或 gzip)
        with open(task.input_file_path, 'rb') as f:
            raw = f.read()
        try:
            content = gzip.decompress(raw).decode('utf-8')
        except gzip.BadGzipFile:
            content = raw.decode('utf-8')
        assert 'Mock PO input data' in content
        assert '3896' in content

        # 验证 Mock Server 收到的请求
        requests = test_config['mock_requests']
        assert len(requests) == 1
        req = requests[0]
        assert req['path'].endswith('/api/orengine/po/comptxt')
        assert req['body_text'] == '3896'  # scenarioId 作为纯整数发送

    def test_po_input_scenario_id_non_numeric(self, test_config):
        """PO: scenarioId 为非数字时也能正确发送"""
        from src.tasks.task_manager import Task

        task = Task(
            task_id="test-po-input-002",
            airline="BR",
            optimizer_type="PO",
            parameters={"scenarioId": "abc123"},
            url=test_config['live_server_url'],
            token="test_token",
        )

        result = task._fetch_input_data()
        assert result is True

        req = test_config['mock_requests'][0]
        # 非数字的 scenarioId 作为字符串发送
        assert 'abc123' in req['body_text']


class TestROInput:
    """RO 优化器 input.gz 获取测试"""

    @pytest.mark.parametrize("airline", ["BR", "F8"])
    def test_ro_input_fetch_success(self, test_config, airline):
        """RO: 成功获取 input.gz"""
        from src.tasks.task_manager import Task

        task = Task(
            task_id="test-ro-input-001",
            airline=airline,
            optimizer_type="RO",
            parameters={"scenarioId": "5432"},
            url=test_config['live_server_url'],
            token="test_token",
        )

        result = task._fetch_input_data()
        assert result is True
        assert os.path.exists(task.input_file_path)

        raw = open(task.input_file_path, 'rb').read()
        try:
            content = gzip.decompress(raw).decode('utf-8')
        except gzip.BadGzipFile:
            content = raw.decode('utf-8')
        assert 'Mock RO input data' in content
        assert '5432' in content

        req = test_config['mock_requests'][0]
        assert req['path'].endswith('/api/orengine/ro/comptxt')
        assert req['body_text'] == '5432'


class TestTOInput:
    """TO 优化器 input.gz 获取测试"""

    @pytest.mark.parametrize("airline", ["BR", "F8"])
    def test_to_input_fetch_success(self, test_config, airline):
        """TO: 成功获取 input.gz"""
        from src.tasks.task_manager import Task

        task = Task(
            task_id="test-to-input-001",
            airline=airline,
            optimizer_type="TO",
            parameters={"scenarioId": "9999"},
            url=test_config['live_server_url'],
            token="test_token",
        )

        result = task._fetch_input_data()
        assert result is True
        assert os.path.exists(task.input_file_path)

        raw = open(task.input_file_path, 'rb').read()
        try:
            content = gzip.decompress(raw).decode('utf-8')
        except gzip.BadGzipFile:
            content = raw.decode('utf-8')
        assert 'Mock TO input data' in content

        req = test_config['mock_requests'][0]
        assert req['path'].endswith('/api/orengine/to/comptxt')


class TestRuleChangeFlightInput:
    """Rule/change_flight input.gz 获取测试"""

    @pytest.mark.parametrize("airline", ["BR", "F8"])
    def test_change_flight_input_success(self, test_config, airline):
        """Rule/change_flight: 成功获取 input.gz，验证 JSON 请求体"""
        from src.tasks.task_manager import Task

        params = {
            "category": "change_flight",
            "airline": airline,
            "division": "P",
            "fltId": "162906,162218,162905",
        }

        task = Task(
            task_id="test-cf-input-001",
            airline=airline,
            optimizer_type="Rule",
            parameters=params,
            url=test_config['live_server_url'],
            token="test_token",
        )

        result = task._fetch_input_data()
        assert result is True
        assert os.path.exists(task.input_file_path)

        # 验证请求发送到正确端点
        req = test_config['mock_requests'][0]
        assert req['path'].endswith('/api/orengine/byFlight/comptxt')

        # 验证请求体为正确的 JSON 格式
        body = json.loads(req['body_text'])
        assert body['worksetId'] == 0
        assert body['filiale'] == airline
        assert body['division'] == 'P'
        assert body['flightIds'] == [162906, 162218, 162905]

    def test_change_flight_single_flight(self, test_config):
        """Rule/change_flight: 单个航班 ID"""
        from src.tasks.task_manager import Task

        task = Task(
            task_id="test-cf-input-002",
            airline="BR",
            optimizer_type="Rule",
            parameters={
                "category": "change_flight",
                "airline": "BR",
                "division": "P",
                "fltId": "162906",
            },
            url=test_config['live_server_url'],
            token="test_token",
        )

        result = task._fetch_input_data()
        assert result is True

        body = json.loads(test_config['mock_requests'][0]['body_text'])
        assert body['flightIds'] == [162906]


class TestRuleMandayInput:
    """Rule/manday input.gz 获取测试"""

    @pytest.mark.parametrize("airline", ["BR", "F8"])
    def test_manday_input_success(self, test_config, airline):
        """Rule/manday: 成功获取 input.gz，验证日期范围请求"""
        from src.tasks.task_manager import Task

        params = {
            "category": "manday",
            "startDt": "2025-02-01",
            "endDt": "2025-03-30",
            "division": "P",
        }

        task = Task(
            task_id="test-md-input-001",
            airline=airline,
            optimizer_type="Rule",
            parameters=params,
            url=test_config['live_server_url'],
            token="test_token",
        )

        result = task._fetch_input_data()
        assert result is True
        assert os.path.exists(task.input_file_path)

        req = test_config['mock_requests'][0]
        assert req['path'].endswith('/api/orengine/ro/partial/comptxt')

        body = json.loads(req['body_text'])
        assert body['worksetId'] == 0
        assert body['strDtLoc'] == '2025-02-01'
        assert body['endDtLoc'] == '2025-03-30'
        assert body['division'] == 'P'


class TestRuleMandayByCrewInput:
    """Rule/manday_byCrew input.gz 获取测试"""

    @pytest.mark.parametrize("airline", ["BR", "F8"])
    def test_manday_byCrew_input_success(self, test_config, airline):
        """Rule/manday_byCrew: 成功获取 input.gz，验证 crewIds 列表"""
        from src.tasks.task_manager import Task

        params = {
            "category": "manday_byCrew",
            "startDt": "2024-09-12",
            "endDt": "2024-09-30",
            "division": "P",
            "crewIds": "I73313,H47887,I73647",
        }

        task = Task(
            task_id="test-mbc-input-001",
            airline=airline,
            optimizer_type="Rule",
            parameters=params,
            url=test_config['live_server_url'],
            token="test_token",
        )

        result = task._fetch_input_data()
        assert result is True
        assert os.path.exists(task.input_file_path)

        req = test_config['mock_requests'][0]
        assert req['path'].endswith('/api/orengine/byCrew/comptxt')

        body = json.loads(req['body_text'])
        assert body['worksetId'] == 0
        assert body['start'] == '2024-09-12'
        assert body['end'] == '2024-09-30'
        assert body['division'] == 'P'
        assert body['crewIds'] == ['I73313', 'H47887', 'I73647']


class TestInputErrorPaths:
    """Input 获取错误路径测试"""

    def test_rule_missing_category(self, test_config):
        """Rule 类型缺少 category 参数应抛出 InputFetchError"""
        from src.tasks.task_manager import Task
        from src.exceptions import InputFetchError

        task = Task(
            task_id="test-err-001",
            airline="BR",
            optimizer_type="Rule",
            parameters={},  # 缺少 category
            url=test_config['live_server_url'],
            token="test_token",
        )

        with pytest.raises(InputFetchError, match="category"):
            task._fetch_input_data()

    def test_rule_invalid_category(self, test_config):
        """Rule 类型使用不存在的 category 应抛出 InputFetchError"""
        from src.tasks.task_manager import Task
        from src.exceptions import InputFetchError

        task = Task(
            task_id="test-err-002",
            airline="BR",
            optimizer_type="Rule",
            parameters={"category": "nonexistent_category"},
            url=test_config['live_server_url'],
            token="test_token",
        )

        with pytest.raises(InputFetchError, match="nonexistent_category"):
            task._fetch_input_data()

    def test_live_server_unreachable(self, test_config):
        """Live Server 不可达时应抛出 InputFetchError"""
        from src.tasks.task_manager import Task
        from src.exceptions import InputFetchError

        task = Task(
            task_id="test-err-003",
            airline="BR",
            optimizer_type="PO",
            parameters={"scenarioId": "1234"},
            url="http://127.0.0.1:1",  # 不可达的端口
            token="test_token",
        )

        with pytest.raises(InputFetchError, match="获取input.gz失败"):
            task._fetch_input_data()

    def test_server_integration_disabled_skips_fetch(self, test_config):
        """server_integration=False 时应跳过获取，返回 False"""
        from src.tasks.task_manager import Task
        from src.config.config import config_manager

        # 临时将 PO 的 server_integration 设为 False
        po_config = config_manager.get_optimizer_config("BR", "PO")
        original = po_config.server_integration
        po_config.server_integration = False

        try:
            task = Task(
                task_id="test-skip-001",
                airline="BR",
                optimizer_type="PO",
                parameters={"scenarioId": "1234"},
                url=test_config['live_server_url'],
                token="test_token",
            )

            result = task._fetch_input_data()
            assert result is False
            assert len(test_config['mock_requests']) == 0  # 未发送请求
        finally:
            po_config.server_integration = original


class TestInputFileSize:
    """验证不同大小的 input.gz 都能正确处理"""

    def test_input_file_saved_with_correct_size(self, test_config):
        """验证 input.gz 文件大小大于 0"""
        from src.tasks.task_manager import Task

        task = Task(
            task_id="test-size-001",
            airline="BR",
            optimizer_type="PO",
            parameters={"scenarioId": "100"},
            url=test_config['live_server_url'],
            token="test_token",
        )

        task._fetch_input_data()
        file_size = os.path.getsize(task.input_file_path)
        assert file_size > 0
