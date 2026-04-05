"""
Output 接口测试 — 测试向 Live Server 提交 output.gz

覆盖所有 6 种优化器类型:
- PO, RO, TO
- Rule/change_flight, Rule/manday, Rule/manday_byCrew

验证:
- HTTP 请求正确发送到 Mock Live Server 的 output 端点
- 请求 URL 正确
- 请求 body 为 gzip 压缩的二进制数据
- 提交成功后返回 True
- 输出文件不存在时抛出 OutputSubmitError
"""
import gzip
import json
import os

import pytest


def _create_mock_output_gz(working_dir: str, content: str = "mock output data") -> str:
    """在工作目录中创建模拟的 output.gz 文件"""
    output_path = os.path.join(working_dir, "output.gz")
    with gzip.open(output_path, 'wb') as f:
        f.write(content.encode('utf-8'))
    return output_path


class TestPOOutput:
    """PO 优化器 output.gz 提交测试"""

    @pytest.mark.parametrize("airline", ["BR", "F8"])
    def test_po_output_submit_success(self, test_config, airline):
        """PO: 成功提交 output.gz"""
        from src.tasks.task_manager import Task

        task = Task(
            task_id="test-po-out-001",
            airline=airline,
            optimizer_type="PO",
            parameters={"scenarioId": "3896"},
            url=test_config['live_server_url'],
            token="test_token",
        )

        # 创建模拟的 output.gz
        _create_mock_output_gz(task.working_dir, f"PO output for {airline}")

        result = task._submit_output_data()
        assert result is True

        # 验证请求发送到正确端点
        req = test_config['mock_requests'][0]
        assert req['path'].endswith('/api/orengine/po/solution')

        # 验证发送的是二进制数据
        assert isinstance(req['body'], bytes)
        assert len(req['body']) > 0


class TestROOutput:
    """RO 优化器 output.gz 提交测试"""

    @pytest.mark.parametrize("airline", ["BR", "F8"])
    def test_ro_output_submit_success(self, test_config, airline):
        """RO: 成功提交 output.gz"""
        from src.tasks.task_manager import Task

        task = Task(
            task_id="test-ro-out-001",
            airline=airline,
            optimizer_type="RO",
            parameters={"scenarioId": "5432"},
            url=test_config['live_server_url'],
            token="test_token",
        )

        _create_mock_output_gz(task.working_dir, f"RO output for {airline}")

        result = task._submit_output_data()
        assert result is True

        req = test_config['mock_requests'][0]
        assert req['path'].endswith('/api/orengine/ro/solution')


class TestTOOutput:
    """TO 优化器 output.gz 提交测试"""

    @pytest.mark.parametrize("airline", ["BR", "F8"])
    def test_to_output_submit_success(self, test_config, airline):
        """TO: 成功提交 output.gz"""
        from src.tasks.task_manager import Task

        task = Task(
            task_id="test-to-out-001",
            airline=airline,
            optimizer_type="TO",
            parameters={"scenarioId": "9999"},
            url=test_config['live_server_url'],
            token="test_token",
        )

        _create_mock_output_gz(task.working_dir, f"TO output for {airline}")

        result = task._submit_output_data()
        assert result is True

        req = test_config['mock_requests'][0]
        assert req['path'].endswith('/api/orengine/to/solution')


class TestRuleChangeFlightOutput:
    """Rule/change_flight output.gz 提交测试"""

    @pytest.mark.parametrize("airline", ["BR", "F8"])
    def test_change_flight_output_success(self, test_config, airline):
        """Rule/change_flight: 成功提交 output.gz"""
        from src.tasks.task_manager import Task

        task = Task(
            task_id="test-cf-out-001",
            airline=airline,
            optimizer_type="Rule",
            parameters={
                "category": "change_flight",
                "airline": airline,
                "division": "P",
                "fltId": "162906,162218",
            },
            url=test_config['live_server_url'],
            token="test_token",
        )

        _create_mock_output_gz(task.working_dir, f"change_flight output for {airline}")

        result = task._submit_output_data()
        assert result is True

        req = test_config['mock_requests'][0]
        assert req['path'].endswith('/api/orengine/byFlight/save/csv')


class TestRuleMandayOutput:
    """Rule/manday output.gz 提交测试"""

    @pytest.mark.parametrize("airline", ["BR", "F8"])
    def test_manday_output_success(self, test_config, airline):
        """Rule/manday: 成功提交 output.gz"""
        from src.tasks.task_manager import Task

        task = Task(
            task_id="test-md-out-001",
            airline=airline,
            optimizer_type="Rule",
            parameters={
                "category": "manday",
                "startDt": "2025-02-01",
                "endDt": "2025-03-30",
                "division": "P",
            },
            url=test_config['live_server_url'],
            token="test_token",
        )

        _create_mock_output_gz(task.working_dir, f"manday output for {airline}")

        result = task._submit_output_data()
        assert result is True

        req = test_config['mock_requests'][0]
        assert req['path'].endswith('/api/crewMandayFd/partlySave/csv/comp')


class TestRuleMandayByCrewOutput:
    """Rule/manday_byCrew output.gz 提交测试"""

    @pytest.mark.parametrize("airline", ["BR", "F8"])
    def test_manday_byCrew_output_success(self, test_config, airline):
        """Rule/manday_byCrew: 成功提交 output.gz"""
        from src.tasks.task_manager import Task

        task = Task(
            task_id="test-mbc-out-001",
            airline=airline,
            optimizer_type="Rule",
            parameters={
                "category": "manday_byCrew",
                "startDt": "2024-09-12",
                "endDt": "2024-09-30",
                "division": "P",
                "crewIds": "I73313,H47887",
            },
            url=test_config['live_server_url'],
            token="test_token",
        )

        _create_mock_output_gz(task.working_dir, f"manday_byCrew output for {airline}")

        result = task._submit_output_data()
        assert result is True

        req = test_config['mock_requests'][0]
        assert req['path'].endswith('/api/crewMandayFd/partlySave/csv/comp')


class TestOutputErrorPaths:
    """Output 提交错误路径测试"""

    def test_output_file_not_exists(self, test_config):
        """output.gz 文件不存在时应抛出 OutputSubmitError"""
        from src.tasks.task_manager import Task
        from src.exceptions import OutputSubmitError

        task = Task(
            task_id="test-out-err-001",
            airline="BR",
            optimizer_type="PO",
            parameters={"scenarioId": "1234"},
            url=test_config['live_server_url'],
            token="test_token",
        )
        # 不创建 output.gz 文件

        with pytest.raises(OutputSubmitError, match="输出文件不存在"):
            task._submit_output_data()

    def test_server_integration_disabled_skips_submit(self, test_config):
        """server_integration=False 时应跳过提交"""
        from src.tasks.task_manager import Task
        from src.config.config import config_manager

        po_config = config_manager.get_optimizer_config("BR", "PO")
        original = po_config.server_integration
        po_config.server_integration = False

        try:
            task = Task(
                task_id="test-out-skip-001",
                airline="BR",
                optimizer_type="PO",
                parameters={"scenarioId": "1234"},
                url=test_config['live_server_url'],
                token="test_token",
            )

            result = task._submit_output_data()
            assert result is False
            assert len(test_config['mock_requests']) == 0
        finally:
            po_config.server_integration = original

    def test_output_submit_to_unreachable_server(self, test_config):
        """Live Server 不可达时应抛出 OutputSubmitError"""
        from src.tasks.task_manager import Task
        from src.exceptions import OutputSubmitError

        task = Task(
            task_id="test-out-err-002",
            airline="BR",
            optimizer_type="PO",
            parameters={"scenarioId": "1234"},
            url="http://127.0.0.1:1",  # 不可达
            token="test_token",
        )
        _create_mock_output_gz(task.working_dir)

        with pytest.raises(OutputSubmitError, match="提交output.gz失败"):
            task._submit_output_data()


class TestOutputDataIntegrity:
    """Output 数据完整性测试"""

    def test_output_data_is_gzip(self, test_config):
        """验证提交到 Live Server 的数据确实是 gzip 格式"""
        from src.tasks.task_manager import Task

        task = Task(
            task_id="test-integrity-001",
            airline="BR",
            optimizer_type="PO",
            parameters={"scenarioId": "1234"},
            url=test_config['live_server_url'],
            token="test_token",
        )

        original_content = "This is test output data with special chars: 中文测试"
        _create_mock_output_gz(task.working_dir, original_content)
        task._submit_output_data()

        req = test_config['mock_requests'][0]
        # gzip magic number: 0x1f 0x8b
        assert req['body'][:2] == b'\x1f\x8b'

        # 解压验证内容完整
        decompressed = gzip.decompress(req['body']).decode('utf-8')
        assert decompressed == original_content
