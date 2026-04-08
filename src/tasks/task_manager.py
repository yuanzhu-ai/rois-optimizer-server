import os
import uuid
import subprocess
import threading
import time
import logging
from typing import Dict, Optional, List
from enum import Enum
from src.optimizers.optimizer_manager import optimizer_manager
from src.config.config import config_manager
from src.tasks.redis_manager import redis_manager
from src.utils.http_client import create_live_server_client
from src.utils.rule_request_builder import RuleRequestBuilder
from src.files.file_manager import file_manager
from src.exceptions import (
    OptimizerNotFoundError, OptimizerExecutionError,
    TaskNotFoundError, TaskLimitError, TaskStateError,
    InputFetchError, OutputSubmitError,
)

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    PENDING = "pending"      # 待执行
    RUNNING = "running"      # 运行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"        # 失败
    STOPPED = "stopped"      # 已停止


class Task:
    def __init__(self, task_id: str, airline: str, optimizer_type: str, parameters: dict = None,
                 url: str = None, token: str = None, user: str = None):
        self.task_id = task_id
        self.airline = airline
        self.optimizer_type = optimizer_type
        self.parameters = parameters or {}
        self.url = url  # Live Server URL
        self.token = token  # 认证token (用于调用Live Server)
        self.user = user  # 用户名
        self.status = TaskStatus.PENDING
        self.progress = 0
        self.start_time = None
        self.end_time = None
        self.error_message = None
        self.working_dir = optimizer_manager.prepare_working_dir(airline, optimizer_type, self.parameters, task_id[:8])
        self.process = None
        self.server_id = redis_manager.get_server_id()
        self.input_file_path = None
        self.output_file_path = None
        self._stdout_lines: List[str] = []
        self._stderr_lines: List[str] = []

        # 初始化时保存到Redis
        self._save_to_redis()

    def _save_to_redis(self):
        """保存任务数据到Redis"""
        task_data = {
            'task_id': self.task_id,
            'airline': self.airline,
            'optimizer_type': self.optimizer_type,
            'parameters': self.parameters,
            'status': self.status.value,
            'progress': self.progress,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'error_message': self.error_message,
            'server_id': self.server_id
        }
        redis_manager.set_task(self.task_id, task_data)

    def _server_integration_enabled(self, optimizer_config) -> bool:
        """判断优化器是否启用 Live Server 集成"""
        return bool(getattr(optimizer_config, 'server_integration', False))

    def _get_rule_category(self) -> str:
        """Rule 专用：获取并校验 category 参数，缺失时抛 ValueError"""
        category = self.parameters.get("category")
        if not category:
            raise ValueError("Rule类型缺少category参数")
        return category

    def _resolve_url_path(self, optimizer_config, direction: str) -> str:
        """按优化器类型解析 input/output URL 路径

        Rule 走 optimizer_config.categories[category].url.<direction>；
        PO/RO/TO 走 optimizer_config.url.<direction>。

        Args:
            direction: 'input' 或 'output'
        """
        if self.optimizer_type == "Rule":
            category = self._get_rule_category()
            if category not in optimizer_config.categories:
                raise ValueError(f"Rule category '{category}' 不存在")
            url_cfg = optimizer_config.categories[category].url
        else:
            url_cfg = optimizer_config.url
        return getattr(url_cfg, direction)

    def _build_input_request_body(self):
        """按优化器类型构造 Live Server input 请求体

        - Rule: 通过 RuleRequestBuilder 构造 dict（_post 会以 json= 发送）
        - PO/RO/TO: 发送纯整数 scenarioId（_post 会以 str(int) 作为原始 body）
        """
        if self.optimizer_type == "Rule":
            return RuleRequestBuilder.build_request(self._get_rule_category(), self.parameters)

        scenario_id = self.parameters.get("scenarioId")
        if not scenario_id:
            return None
        try:
            return int(scenario_id)
        except (ValueError, TypeError):
            return scenario_id

    def _resolve_live_server_auth(self) -> (str, str):
        """解析调用 Live Server 时使用的 base_url 和 token，未传时回退到默认值"""
        base_url = self.url if self.url else f"http://localhost/{self.airline.lower()}"
        token = self.token if self.token else ""
        return base_url, token

    def _fetch_input_data(self) -> bool:
        """从Live Server获取input.gz文件

        Returns:
            True: 成功获取input.gz
            False: server_integration未启用，不需要获取

        Raises:
            InputFetchError: 获取input.gz失败
        """
        optimizer_config = config_manager.get_optimizer_config(self.airline, self.optimizer_type)

        if not self._server_integration_enabled(optimizer_config):
            logger.info("[Task %s] server_integration未启用，跳过获取input.gz", self.task_id)
            return False

        try:
            input_url = self._resolve_url_path(optimizer_config, "input")
            request_data = self._build_input_request_body()
        except ValueError as e:
            raise InputFetchError(f"[Task {self.task_id}] {e}") from e

        base_url, token = self._resolve_live_server_auth()

        logger.info("[Task %s] 正在从Live Server获取input.gz, URL: %s, API: %s",
                    self.task_id, base_url, input_url)
        logger.debug("[Task %s] 请求数据: %s", self.task_id, request_data)

        try:
            with create_live_server_client(base_url, token) as client:
                response_data = client.get_input_data(
                    airline=self.airline,
                    url_path=input_url,
                    data=request_data,
                )
        except Exception as e:
            raise InputFetchError(f"[Task {self.task_id}] 获取input.gz失败: {e}") from e

        # 保存input.gz文件
        self.input_file_path = os.path.join(self.working_dir, "input.gz")
        with open(self.input_file_path, 'wb') as f:
            f.write(response_data)

        logger.info("[Task %s] 成功获取input.gz，大小: %d bytes", self.task_id, len(response_data))
        return True

    def _submit_output_data(self) -> bool:
        """向Live Server提交output.gz文件

        Returns:
            True: 成功提交
            False: server_integration未启用，不需要提交

        Raises:
            OutputSubmitError: 提交output.gz失败
        """
        optimizer_config = config_manager.get_optimizer_config(self.airline, self.optimizer_type)

        if not self._server_integration_enabled(optimizer_config):
            logger.info("[Task %s] server_integration未启用，跳过提交output.gz", self.task_id)
            return False

        self.output_file_path = os.path.join(self.working_dir, "output.gz")
        if not os.path.exists(self.output_file_path):
            raise OutputSubmitError(f"[Task {self.task_id}] 输出文件不存在: {self.output_file_path}")

        try:
            output_url = self._resolve_url_path(optimizer_config, "output")
        except ValueError as e:
            raise OutputSubmitError(f"[Task {self.task_id}] {e}") from e

        base_url, token = self._resolve_live_server_auth()

        logger.info("[Task %s] 正在向Live Server提交output.gz, URL: %s, API: %s",
                    self.task_id, base_url, output_url)

        try:
            with open(self.output_file_path, 'rb') as f:
                output_data = f.read()

            with create_live_server_client(base_url, token) as client:
                client.submit_output_data(
                    airline=self.airline,
                    url_path=output_url,
                    data=output_data,
                )
        except Exception as e:
            raise OutputSubmitError(f"[Task {self.task_id}] 提交output.gz失败: {e}") from e

        logger.info("[Task %s] 成功提交output.gz，大小: %d bytes", self.task_id, len(output_data))
        return True

    def _build_command(self, optimizer) -> List[str]:
        """构建优化器执行命令

        Returns:
            命令参数列表

        Raises:
            OptimizerExecutionError: 可执行文件不存在
        """
        # 通过策略模式统一获取可执行文件路径（Rule/PO/RO/TO 均由各自的 Optimizer 子类处理）
        exec_path = optimizer.get_executable_path(self.parameters)

        if not exec_path:
            raise OptimizerExecutionError(
                f"[Task {self.task_id}] 优化器 {self.airline}/{self.optimizer_type} 未配置可执行文件路径"
            )

        # 将相对路径转换为绝对路径
        if not os.path.isabs(exec_path):
            exec_path = os.path.abspath(exec_path)

        # 检查可执行文件是否存在
        if not os.path.exists(exec_path):
            logger.warning(
                "[Task %s] 可执行文件不存在: %s，将尝试直接执行（可能在PATH中）",
                self.task_id, exec_path
            )

        # 构建命令：可执行文件 + 工作目录作为参数
        cmd = [exec_path, self.working_dir]

        # 如果有 input.gz，追加输入文件路径
        if self.input_file_path and os.path.exists(self.input_file_path):
            cmd.append(self.input_file_path)

        return cmd

    def start(self):
        """启动任务

        Returns:
            True: 启动成功

        Raises:
            OptimizerNotFoundError: 优化器不存在
            InputFetchError: 获取输入文件失败
            OptimizerExecutionError: 启动进程失败
        """
        optimizer = optimizer_manager.get_optimizer(self.airline, self.optimizer_type)
        if not optimizer:
            self.status = TaskStatus.FAILED
            self.error_message = f"优化器 {self.optimizer_type} 不存在"
            self._save_to_redis()
            raise OptimizerNotFoundError(self.error_message)

        # 从Live Server获取input.gz（如果启用了server_integration）
        try:
            self._fetch_input_data()
        except InputFetchError as e:
            self.status = TaskStatus.FAILED
            self.error_message = str(e)
            self._save_to_redis()
            raise

        # 构建执行命令
        try:
            cmd = self._build_command(optimizer)
        except OptimizerExecutionError as e:
            self.status = TaskStatus.FAILED
            self.error_message = str(e)
            self._save_to_redis()
            raise

        try:
            logger.info("[Task %s] 执行命令: %s, 工作目录: %s", self.task_id, cmd, self.working_dir)

            self.process = subprocess.Popen(
                cmd,
                cwd=self.working_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            self.status = TaskStatus.RUNNING
            self.start_time = time.time()
            self._save_to_redis()

            logger.info("[Task %s] 任务已启动, airline=%s, type=%s, pid=%d",
                         self.task_id, self.airline, self.optimizer_type, self.process.pid)

            # 启动 stdout/stderr 读取线程（防止管道缓冲区满导致死锁）
            stdout_thread = threading.Thread(
                target=self._read_stream, args=(self.process.stdout, self._stdout_lines, "stdout"),
                name=f"stdout-{self.task_id[:8]}", daemon=True
            )
            stderr_thread = threading.Thread(
                target=self._read_stream, args=(self.process.stderr, self._stderr_lines, "stderr"),
                name=f"stderr-{self.task_id[:8]}", daemon=True
            )
            stdout_thread.start()
            stderr_thread.start()

            # 启动监控线程
            monitor_thread = threading.Thread(
                target=self._monitor_task,
                args=(stdout_thread, stderr_thread),
                name=f"monitor-{self.task_id[:8]}", daemon=True
            )
            monitor_thread.start()

            return True
        except Exception as e:
            self.status = TaskStatus.FAILED
            self.error_message = str(e)
            self._save_to_redis()
            raise OptimizerExecutionError(f"[Task {self.task_id}] 启动失败: {e}") from e

    def _read_stream(self, stream, lines: List[str], name: str):
        """持续读取子进程的输出流，防止管道缓冲区满导致死锁"""
        try:
            for line in stream:
                line = line.rstrip('\n')
                lines.append(line)
                # 尝试从stdout中解析进度信息
                if name == "stdout":
                    self._parse_progress(line)
            stream.close()
        except Exception as e:
            logger.debug("[Task %s] 读取%s结束: %s", self.task_id, name, e)

    def _parse_progress(self, line: str):
        """从优化器输出中解析进度信息

        支持的格式:
        - PROGRESS:50      (直接百分比)
        - PROGRESS:50/100  (当前/总数)
        """
        line = line.strip()
        if not line.startswith("PROGRESS:"):
            return

        try:
            value = line[len("PROGRESS:"):]
            if "/" in value:
                current, total = value.split("/", 1)
                progress = int(int(current) / int(total) * 100)
            else:
                progress = int(value)

            progress = max(0, min(100, progress))
            self.progress = progress
            redis_manager.update_task_progress(self.task_id, progress)
        except (ValueError, ZeroDivisionError):
            pass

    def stop(self):
        """停止任务"""
        if self.status == TaskStatus.RUNNING and self.process:
            try:
                logger.info("[Task %s] 正在停止任务, pid=%d", self.task_id, self.process.pid)
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    logger.warning("[Task %s] terminate超时，强制kill进程", self.task_id)
                    self.process.kill()
                    self.process.wait(timeout=3)
                self.status = TaskStatus.STOPPED
                self.end_time = time.time()
                self._save_to_redis()
                # 搬运被停止的任务目录到 finished/<airline>/<task_dir>_stop/
                file_manager.move_to_finished(self.working_dir, self.airline, suffix="_stop")
                logger.info("[Task %s] 任务已停止", self.task_id)
                return True
            except Exception as e:
                self.error_message = str(e)
                self._save_to_redis()
                logger.error("[Task %s] 停止任务异常: %s", self.task_id, e, exc_info=True)
                return False
        return False

    def _monitor_task(self, stdout_thread: threading.Thread, stderr_thread: threading.Thread):
        """监控任务执行状态"""
        if not self.process:
            return

        task_timeout = config_manager.get_config().tasks.timeout

        # 等待进程结束（带超时）
        try:
            self.process.wait(timeout=task_timeout)
        except subprocess.TimeoutExpired:
            logger.warning("[Task %s] 进程执行超时(%ds)，强制终止", self.task_id, task_timeout)
            self.process.kill()
            self.process.wait(timeout=10)

        # 等待 stdout/stderr 读取线程完成
        stdout_thread.join(timeout=5)
        stderr_thread.join(timeout=5)

        if self.status == TaskStatus.RUNNING:
            if self.process.returncode == 0:
                # 优化器执行成功
                self.progress = 100
                redis_manager.update_task_progress(self.task_id, 100)

                # 提交输出文件到Live Server，提交失败视为任务失败
                submit_failed = False
                try:
                    self._submit_output_data()
                except OutputSubmitError as e:
                    logger.error("[Task %s] %s", self.task_id, e)
                    submit_failed = True
                    self.status = TaskStatus.FAILED
                    self.error_message = str(e)

                if submit_failed:
                    # 提交失败：归档到 finished/<airline>/<task_dir>_submit_failed/
                    file_manager.move_to_finished(self.working_dir, self.airline, suffix="_submit_failed")
                    logger.error("[Task %s] 任务因output.gz提交失败而失败", self.task_id)
                else:
                    # 移动结果文件到finished目录
                    file_manager.move_to_finished(self.working_dir, self.airline)
                    self.status = TaskStatus.COMPLETED
                    logger.info("[Task %s] 任务执行完成", self.task_id)
            else:
                stderr_text = "\n".join(self._stderr_lines)
                self.status = TaskStatus.FAILED
                self.error_message = stderr_text or f"进程退出码: {self.process.returncode}"
                logger.error("[Task %s] 任务执行失败, returncode=%d, stderr=%s",
                             self.task_id, self.process.returncode, stderr_text[:500])
                # 搬运失败任务目录到 finished/<airline>/<task_dir>_failed/
                file_manager.move_to_finished(self.working_dir, self.airline, suffix="_failed")
            self.end_time = time.time()
            self._save_to_redis()

    def get_status(self) -> str:
        """获取任务状态"""
        return self.status.value

    def get_progress(self) -> int:
        """获取任务进度"""
        return self.progress


class TaskManager:
    # 已完成任务的保留时间（秒），超过后自动清理
    COMPLETED_TASK_TTL = 3600  # 1小时

    def __init__(self):
        self.tasks: Dict[str, Task] = {}  # task_id -> Task
        self.airline_tasks: Dict[str, List[str]] = {}  # airline -> list of task_ids
        self.max_concurrent = config_manager.get_config().tasks.max_concurrent
        self.lock = threading.Lock()

    def create_task(self, airline: str, optimizer_type: str, parameters: dict = None,
                   url: str = None, token: str = None, user: str = None) -> str:
        """创建新任务

        Returns:
            task_id

        Raises:
            OptimizerNotFoundError: 优化器不可用
            TaskLimitError: 已达最大并发数
        """
        if not optimizer_manager.validate_optimizer(airline, optimizer_type):
            raise OptimizerNotFoundError(f"航司 {airline} 的优化器 {optimizer_type} 不可用")

        with self.lock:
            local_running_count = len([t for t in self.tasks.values() if t.status == TaskStatus.RUNNING])
            if local_running_count >= self.max_concurrent:
                raise TaskLimitError(f"已达最大并发数 {self.max_concurrent}")

            task_id = str(uuid.uuid4())
            task = Task(task_id, airline, optimizer_type, parameters, url, token, user)
            self.tasks[task_id] = task

            if airline not in self.airline_tasks:
                self.airline_tasks[airline] = []
            self.airline_tasks[airline].append(task_id)

        logger.info("任务创建成功: task_id=%s, airline=%s, type=%s", task_id, airline, optimizer_type)
        return task_id

    def start_task(self, task_id: str) -> bool:
        """启动任务

        Raises:
            TaskNotFoundError: 任务不存在
            TaskStateError: 任务状态不正确
            TaskLimitError: 已达最大并发数
        """
        with self.lock:
            task = self.tasks.get(task_id)
            if not task:
                task_data = redis_manager.get_task(task_id)
                if task_data:
                    raise TaskStateError(f"任务 {task_id} 在其他服务器上，无法在本地启动")
                raise TaskNotFoundError(f"任务 {task_id} 不存在")

            if task.status != TaskStatus.PENDING:
                raise TaskStateError(f"任务 {task_id} 当前状态为 {task.status.value}，无法启动")

            local_running_count = len([t for t in self.tasks.values() if t.status == TaskStatus.RUNNING])
            if local_running_count >= self.max_concurrent:
                raise TaskLimitError(f"已达最大并发数 {self.max_concurrent}")

        # 在锁外启动任务
        return task.start()

    def stop_task(self, task_id: str) -> bool:
        """停止任务"""
        task = None
        with self.lock:
            task = self.tasks.get(task_id)

        if task:
            return task.stop()

        # 检查Redis中的任务（可能在其他服务器）
        task_data = redis_manager.get_task(task_id)
        if task_data:
            redis_manager.publish_task_event(task_id, "stop", {})
            logger.info("已通过Redis发布停止事件: task_id=%s", task_id)
            return True

        return False

    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        with self.lock:
            task = self.tasks.get(task_id)
            if task:
                return task

        # 检查Redis中的任务
        task_data = redis_manager.get_task(task_id)
        if task_data:
            task = Task(
                task_id=task_data['task_id'],
                airline=task_data['airline'],
                optimizer_type=task_data['optimizer_type'],
                parameters=task_data['parameters']
            )
            task.status = TaskStatus(task_data['status'])
            task.progress = task_data['progress']
            task.start_time = task_data['start_time']
            task.end_time = task_data['end_time']
            task.error_message = task_data['error_message']
            return task

        return None

    def get_all_tasks(self, airline: str = None) -> List[dict]:
        """获取所有任务信息"""
        redis_tasks = redis_manager.get_all_tasks(airline)

        with self.lock:
            if airline:
                task_ids = self.airline_tasks.get(airline, [])
                local_tasks = [self.tasks[task_id] for task_id in task_ids if task_id in self.tasks]
            else:
                local_tasks = list(self.tasks.values())

        local_tasks_dict = [{
            "task_id": task.task_id,
            "airline": task.airline,
            "optimizer_type": task.optimizer_type,
            "status": task.get_status(),
            "progress": task.get_progress(),
            "start_time": task.start_time,
            "end_time": task.end_time,
            "error_message": task.error_message
        } for task in local_tasks]

        task_map = {}
        for task in redis_tasks:
            task_map[task['task_id']] = task
        for task in local_tasks_dict:
            task_map[task['task_id']] = task

        return list(task_map.values())

    def get_running_tasks(self, airline: str = None) -> List[dict]:
        """获取运行中任务"""
        redis_tasks = redis_manager.get_running_tasks(airline)

        with self.lock:
            if airline:
                task_ids = self.airline_tasks.get(airline, [])
                local_tasks = [self.tasks[task_id] for task_id in task_ids if task_id in self.tasks and self.tasks[task_id].status == TaskStatus.RUNNING]
            else:
                local_tasks = [t for t in self.tasks.values() if t.status == TaskStatus.RUNNING]

        local_tasks_dict = [{
            "task_id": task.task_id,
            "airline": task.airline,
            "optimizer_type": task.optimizer_type,
            "status": task.get_status(),
            "progress": task.get_progress(),
            "start_time": task.start_time
        } for task in local_tasks]

        task_map = {}
        for task in redis_tasks:
            task_map[task['task_id']] = task
        for task in local_tasks_dict:
            task_map[task['task_id']] = task

        return list(task_map.values())

    def cleanup_tasks(self):
        """清理已完成的任务（超过TTL的）"""
        current_time = time.time()
        with self.lock:
            completed_task_ids = []
            for task_id, task in self.tasks.items():
                if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.STOPPED]:
                    if task.end_time and (current_time - task.end_time) > self.COMPLETED_TASK_TTL:
                        completed_task_ids.append(task_id)

            if completed_task_ids:
                logger.info("清理已完成任务: %d 个", len(completed_task_ids))

            for task_id in completed_task_ids:
                task = self.tasks[task_id]
                if task.airline in self.airline_tasks:
                    if task_id in self.airline_tasks[task.airline]:
                        self.airline_tasks[task.airline].remove(task_id)
                del self.tasks[task_id]
                redis_manager.delete_task(task_id)

    def stop_all_tasks(self):
        """停止所有运行中的任务（服务关闭时调用）"""
        with self.lock:
            running_tasks = [t for t in self.tasks.values() if t.status == TaskStatus.RUNNING]

        for task in running_tasks:
            logger.info("服务关闭，正在停止任务: %s", task.task_id)
            task.stop()


# 全局任务管理器实例
task_manager = TaskManager()
