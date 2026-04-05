"""
测试公共 fixture 模块

提供:
- Mock Live Server (模拟所有 input/output 端点)
- Mock 优化器脚本 (模拟 PO/RO/TO/Rule 可执行文件)
- FastAPI TestClient
- 临时工作目录
- 配置重置
"""
import gzip
import json
import os
import shutil
import stat
import sys
import tempfile
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, List, Tuple

import pytest

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ============================================================
# Mock Live Server
# ============================================================

class MockLiveServerHandler(BaseHTTPRequestHandler):
    """模拟 Live Server 的所有 input/output 端点"""

    # 类级别变量，记录所有收到的请求
    received_requests: List[Dict] = []

    def log_message(self, format, *args):
        """抑制默认日志输出"""
        pass

    def _read_body(self) -> bytes:
        content_length = int(self.headers.get('Content-Length', 0))
        return self.rfile.read(content_length) if content_length > 0 else b''

    def _send_gzip_response(self, data: str):
        """发送 gzip 压缩响应 (模拟 input.gz)"""
        compressed = gzip.compress(data.encode('utf-8'))
        self.send_response(200)
        self.send_header('Content-Type', 'application/octet-stream')
        self.send_header('Content-Encoding', 'gzip')
        self.send_header('Content-Length', str(len(compressed)))
        self.end_headers()
        self.wfile.write(compressed)

    def _send_ok_response(self):
        """发送简单 OK 响应 (模拟 output 提交成功)"""
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain')
        self.send_header('Content-Length', '2')
        self.end_headers()
        self.wfile.write(b'OK')

    def _send_error(self, code: int, message: str):
        self.send_response(code)
        self.send_header('Content-Type', 'text/plain')
        body = message.encode('utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        body = self._read_body()
        path = self.path

        # 记录请求
        record = {
            'method': 'POST',
            'path': path,
            'headers': dict(self.headers),
            'body': body,
            'body_text': None,
        }
        try:
            record['body_text'] = body.decode('utf-8')
        except UnicodeDecodeError:
            record['body_text'] = f'<binary {len(body)} bytes>'
        MockLiveServerHandler.received_requests.append(record)

        # ---- PO Input ----
        if path.endswith('/api/orengine/po/comptxt'):
            self._send_gzip_response(f'Mock PO input data for scenarioId={body.decode("utf-8", errors="replace")}')

        # ---- PO Output ----
        elif path.endswith('/api/orengine/po/solution'):
            self._send_ok_response()

        # ---- RO Input ----
        elif path.endswith('/api/orengine/ro/comptxt'):
            self._send_gzip_response(f'Mock RO input data for scenarioId={body.decode("utf-8", errors="replace")}')

        # ---- RO Output ----
        elif path.endswith('/api/orengine/ro/solution'):
            self._send_ok_response()

        # ---- TO Input ----
        elif path.endswith('/api/orengine/to/comptxt'):
            self._send_gzip_response(f'Mock TO input data for scenarioId={body.decode("utf-8", errors="replace")}')

        # ---- TO Output ----
        elif path.endswith('/api/orengine/to/solution'):
            self._send_ok_response()

        # ---- Rule: change_flight Input ----
        elif path.endswith('/api/orengine/byFlight/comptxt'):
            self._send_gzip_response(f'Mock change_flight input data: {body.decode("utf-8", errors="replace")}')

        # ---- Rule: change_flight Output ----
        elif path.endswith('/api/orengine/byFlight/save/csv'):
            self._send_ok_response()

        # ---- Rule: manday Input ----
        elif path.endswith('/api/orengine/ro/partial/comptxt'):
            self._send_gzip_response(f'Mock manday input data: {body.decode("utf-8", errors="replace")}')

        # ---- Rule: manday / manday_byCrew Output ----
        elif path.endswith('/api/crewMandayFd/partlySave/csv/comp'):
            self._send_ok_response()

        # ---- Rule: manday_byCrew Input ----
        elif path.endswith('/api/orengine/byCrew/comptxt'):
            self._send_gzip_response(f'Mock manday_byCrew input data: {body.decode("utf-8", errors="replace")}')

        else:
            self._send_error(404, f'Unknown endpoint: {path}')


@pytest.fixture(scope="session")
def mock_live_server():
    """启动 Mock Live Server，整个测试 session 共享"""
    # 清除之前的请求记录
    MockLiveServerHandler.received_requests = []

    server = HTTPServer(('127.0.0.1', 0), MockLiveServerHandler)
    port = server.server_address[1]
    base_url = f'http://127.0.0.1:{port}'

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    yield {
        'server': server,
        'base_url': base_url,
        'port': port,
        'requests': MockLiveServerHandler.received_requests,
    }

    server.shutdown()


@pytest.fixture(autouse=True)
def clear_mock_requests():
    """每个测试前清除请求记录"""
    MockLiveServerHandler.received_requests.clear()
    yield


# ============================================================
# 临时工作目录 & Mock 优化器脚本
# ============================================================

@pytest.fixture()
def temp_workspace(tmp_path):
    """创建临时工作目录结构"""
    workspace = tmp_path / "workspace"
    finished = tmp_path / "finished"
    archive = tmp_path / "archive"
    temp = tmp_path / "temp"

    for d in [workspace, finished, archive, temp]:
        d.mkdir()

    return {
        'root': tmp_path,
        'workspace': str(workspace),
        'finished': str(finished),
        'archive': str(archive),
        'temp': str(temp),
    }


def _create_mock_optimizer_script(path: str, exit_code: int = 0, sleep_seconds: float = 0.1,
                                   produce_output: bool = True, progress_steps: int = 5):
    """创建一个 mock 优化器 shell 脚本

    脚本功能:
    - 读取 input.gz (如果存在)
    - 输出 PROGRESS:N 进度信息
    - 生成 output.gz
    - 以指定退出码退出
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)

    script_content = f"""#!/bin/bash
WORK_DIR="${{1:-.}}"
INPUT_FILE="${{2:-$WORK_DIR/input.gz}}"

# 输出进度
for i in $(seq 1 {progress_steps}); do
    progress=$(( i * 100 / {progress_steps} ))
    echo "PROGRESS:$progress"
    sleep {sleep_seconds}
done

# 生成 output.gz
"""
    if produce_output:
        script_content += """
if [ -f "$INPUT_FILE" ]; then
    echo "Processing input from $INPUT_FILE" | gzip > "$WORK_DIR/output.gz"
else
    echo "No input file, generating default output" | gzip > "$WORK_DIR/output.gz"
fi
"""

    script_content += f"""
exit {exit_code}
"""

    with open(path, 'w') as f:
        f.write(script_content)
    os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return path


@pytest.fixture()
def mock_optimizers(tmp_path):
    """创建所有航司的 mock 优化器脚本，返回脚本路径字典"""
    scripts = {}
    for airline in ['BR', 'F8']:
        airline_dir = tmp_path / "optimizers" / airline
        for opt_type in ['po', 'ro', 'to']:
            path = str(airline_dir / f"{opt_type}.sh")
            _create_mock_optimizer_script(path)
            scripts[f"{airline}/{opt_type}"] = path

        for rule_cat in ['rule_change_flight', 'rule_manday', 'rule_manday_byCrew']:
            path = str(airline_dir / f"{rule_cat}.sh")
            _create_mock_optimizer_script(path)
            scripts[f"{airline}/{rule_cat}"] = path

    return scripts


@pytest.fixture()
def mock_failing_optimizer(tmp_path):
    """创建一个会失败的 mock 优化器脚本"""
    path = str(tmp_path / "failing_optimizer.sh")
    _create_mock_optimizer_script(path, exit_code=1, produce_output=False)
    return path


# ============================================================
# 配置重置 fixture
# ============================================================

@pytest.fixture()
def test_config(temp_workspace, mock_optimizers, mock_live_server):
    """创建测试用配置，覆盖全局 config_manager

    - 使用临时工作目录
    - 使用 mock 优化器脚本路径
    - 禁用认证 (方便测试)
    - 使用 Mock Live Server URL
    """
    from src.config.config import (
        config_manager, Config, ServerConfig, AuthConfig, PathsConfig,
        FileManagementConfig, TasksConfig, RedisConfig, HttpClientConfig,
        AirlineConfig, OptimizersConfig, OptimizerTypeConfig, OptimizerOSConfig,
        OptimizerURLConfig, RuleOptimizerConfig, RuleCategoryConfig, CorsConfig,
    )

    def _make_airline_config(airline: str) -> AirlineConfig:
        return AirlineConfig(
            optimizers=OptimizersConfig(
                PO=OptimizerTypeConfig(
                    name="Pairing Optimizer",
                    linux=OptimizerOSConfig(path=mock_optimizers[f"{airline}/po"]),
                    windows=OptimizerOSConfig(path=mock_optimizers[f"{airline}/po"]),
                    url=OptimizerURLConfig(input="/api/orengine/po/comptxt", output="/api/orengine/po/solution"),
                    server_integration=True,
                ),
                RO=OptimizerTypeConfig(
                    name="Roster Optimizer",
                    linux=OptimizerOSConfig(path=mock_optimizers[f"{airline}/ro"]),
                    windows=OptimizerOSConfig(path=mock_optimizers[f"{airline}/ro"]),
                    url=OptimizerURLConfig(input="/api/orengine/ro/comptxt", output="/api/orengine/ro/solution"),
                    server_integration=True,
                ),
                TO=OptimizerTypeConfig(
                    name="Training Optimizer",
                    linux=OptimizerOSConfig(path=mock_optimizers[f"{airline}/to"]),
                    windows=OptimizerOSConfig(path=mock_optimizers[f"{airline}/to"]),
                    url=OptimizerURLConfig(input="/api/orengine/to/comptxt", output="/api/orengine/to/solution"),
                    server_integration=True,
                ),
                Rule=RuleOptimizerConfig(
                    categories={
                        "change_flight": RuleCategoryConfig(
                            name="Change Flight Rule",
                            linux=OptimizerOSConfig(path=mock_optimizers[f"{airline}/rule_change_flight"]),
                            windows=OptimizerOSConfig(path=mock_optimizers[f"{airline}/rule_change_flight"]),
                            url=OptimizerURLConfig(input="/api/orengine/byFlight/comptxt", output="/api/orengine/byFlight/save/csv"),
                        ),
                        "manday": RuleCategoryConfig(
                            name="Manday Rule",
                            linux=OptimizerOSConfig(path=mock_optimizers[f"{airline}/rule_manday"]),
                            windows=OptimizerOSConfig(path=mock_optimizers[f"{airline}/rule_manday"]),
                            url=OptimizerURLConfig(input="/api/orengine/ro/partial/comptxt", output="/api/crewMandayFd/partlySave/csv/comp"),
                        ),
                        "manday_byCrew": RuleCategoryConfig(
                            name="Manday by Crew Rule",
                            linux=OptimizerOSConfig(path=mock_optimizers[f"{airline}/rule_manday_byCrew"]),
                            windows=OptimizerOSConfig(path=mock_optimizers[f"{airline}/rule_manday_byCrew"]),
                            url=OptimizerURLConfig(input="/api/orengine/byCrew/comptxt", output="/api/crewMandayFd/partlySave/csv/comp"),
                        ),
                    },
                    server_integration=True,
                ),
            )
        )

    test_cfg = Config(
        server=ServerConfig(host="127.0.0.1", port=8000, debug=True, cors=CorsConfig()),
        auth=AuthConfig(enabled=False),
        paths=PathsConfig(
            working_dir=temp_workspace['workspace'],
            finished_dir=temp_workspace['finished'],
            archive_dir=temp_workspace['archive'],
            temp_dir=temp_workspace['temp'],
        ),
        file_management=FileManagementConfig(archive_days=1, cleanup_days=30),
        tasks=TasksConfig(max_concurrent=10, timeout=30),
        redis=RedisConfig(enabled=False),
        http_client=HttpClientConfig(timeout=10),
        airlines={
            "BR": _make_airline_config("BR"),
            "F8": _make_airline_config("F8"),
        },
    )

    # 注入配置
    old_config = config_manager._config
    config_manager._config = test_cfg

    # 重新注册优化器
    from src.optimizers.optimizer_manager import optimizer_manager
    optimizer_manager.optimizers = {}
    optimizer_manager._register_optimizers()

    yield {
        'config': test_cfg,
        'live_server_url': mock_live_server['base_url'],
        'mock_requests': mock_live_server['requests'],
    }

    # 恢复
    config_manager._config = old_config


@pytest.fixture()
def test_task_manager(test_config):
    """创建干净的 TaskManager 实例"""
    from src.tasks.task_manager import TaskManager
    tm = TaskManager()
    yield tm
    # 清理所有运行中的任务
    tm.stop_all_tasks()


@pytest.fixture()
def api_client(test_config):
    """FastAPI TestClient"""
    from fastapi.testclient import TestClient
    from main import app
    with TestClient(app) as client:
        yield client
