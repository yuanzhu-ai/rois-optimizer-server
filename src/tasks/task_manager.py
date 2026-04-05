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
    
    def _fetch_input_data(self) -> bool:
        """从Live Server获取input.gz文件"""
        try:
            optimizer_config = config_manager.get_optimizer_config(self.airline, self.optimizer_type)
            
            if not hasattr(optimizer_config, 'server_integration') or not optimizer_config.server_integration:
                logger.info("[Task %s] server_integration未启用，跳过获取input.gz", self.task_id)
                return False
            
            # 获取输入URL路径
            if self.optimizer_type == "Rule":
                category = self.parameters.get("category")
                if not category:
                    self.error_message = "Rule类型缺少category参数"
                    return False
                if category not in optimizer_config.categories:
                    self.error_message = f"Rule category '{category}' 不存在"
                    return False
                category_config = optimizer_config.categories[category]
                input_url = category_config.url.input
            else:
                input_url = optimizer_config.url.input
            
            base_url = self.url if self.url else f"http://localhost/{self.airline.lower()}"
            token = self.token if self.token else ""
            
            logger.info("[Task %s] 正在从Live Server获取input.gz, URL: %s, API: %s", 
                       self.task_id, base_url, input_url)
            
            # 使用with语句确保HTTP连接正确关闭
            with create_live_server_client(base_url, token) as client:
                # 准备请求数据 - 使用RuleRequestBuilder统一构建
                if self.optimizer_type == "Rule":
                    category = self.parameters.get("category")
                    request_data = RuleRequestBuilder.build_request(category, self.parameters)
                else:
                    # PO/RO/TO类型：发送纯整数scenarioId
                    scenario_id = self.parameters.get("scenarioId")
                    if scenario_id:
                        try:
                            request_data = int(scenario_id)
                        except (ValueError, TypeError):
                            request_data = scenario_id
                    else:
                        request_data = None
                
                logger.debug("[Task %s] 请求数据: %s", self.task_id, request_data)
                
                response_data = client.get_input_data(
                    airline=self.airline,
                    url_path=input_url,
                    data=request_data
                )
            
            # 保存input.gz文件
            self.input_file_path = os.path.join(self.working_dir, "input.gz")
            with open(self.input_file_path, 'wb') as f:
                f.write(response_data)
            
            file_size = len(response_data)
            logger.info("[Task %s] 成功获取input.gz，大小: %d bytes", self.task_id, file_size)
            return True
            
        except Exception as e:
            self.error_message = f"获取input.gz失败: {str(e)}"
            logger.error("[Task %s] %s", self.task_id, self.error_message, exc_info=True)
            return False
    
    def start(self):
        """启动任务"""
        optimizer = optimizer_manager.get_optimizer(self.airline, self.optimizer_type)
        if not optimizer:
            self.status = TaskStatus.FAILED
            self.error_message = f"优化器 {self.optimizer_type} 不存在"
            self._save_to_redis()
            return False
        
        # 尝试从Live Server获取input.gz
        if not self._fetch_input_data():
            logger.warning("[Task %s] 无法获取input.gz，将使用模拟模式", self.task_id)
        
        exec_path = optimizer.get_executable_path()
        
        # 构建执行命令（当前为模拟模式）
        if os.name == "nt":
            cmd = ["cmd.exe", "/c", "echo", f"Running {self.airline} {optimizer.get_name()} optimizer..."]
        else:
            cmd = ["sh", "-c", f"echo Running {self.airline} {optimizer.get_name()} optimizer... && sleep 5"]
        
        try:
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
            
            # 启动监控线程
            monitor_thread = threading.Thread(target=self._monitor_task, name=f"monitor-{self.task_id[:8]}")
            monitor_thread.daemon = True
            monitor_thread.start()
            
            return True
        except Exception as e:
            self.status = TaskStatus.FAILED
            self.error_message = str(e)
            self._save_to_redis()
            logger.error("[Task %s] 启动失败: %s", self.task_id, e, exc_info=True)
            return False
    
    def stop(self):
        """停止任务"""
        if self.status == TaskStatus.RUNNING and self.process:
            try:
                logger.info("[Task %s] 正在停止任务, pid=%d", self.task_id, self.process.pid)
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # terminate超时，强制kill
                    logger.warning("[Task %s] terminate超时，强制kill进程", self.task_id)
                    self.process.kill()
                    self.process.wait(timeout=3)
                self.status = TaskStatus.STOPPED
                self.end_time = time.time()
                self._save_to_redis()
                logger.info("[Task %s] 任务已停止", self.task_id)
                return True
            except Exception as e:
                self.error_message = str(e)
                self._save_to_redis()
                logger.error("[Task %s] 停止任务异常: %s", self.task_id, e, exc_info=True)
                return False
        return False
    
    def _monitor_task(self):
        """监控任务执行状态"""
        if not self.process:
            return
        
        task_timeout = config_manager.get_config().tasks.timeout
        
        # 模拟进度更新
        for i in range(101):
            if self.status != TaskStatus.RUNNING:
                break
            self.progress = i
            redis_manager.update_task_progress(self.task_id, i)
            time.sleep(0.05)
        
        # 等待进程结束（带超时）
        try:
            stdout, stderr = self.process.communicate(timeout=task_timeout)
        except subprocess.TimeoutExpired:
            logger.warning("[Task %s] 进程执行超时(%ds)，强制终止", self.task_id, task_timeout)
            self.process.kill()
            stdout, stderr = self.process.communicate(timeout=10)
        
        if self.status == TaskStatus.RUNNING:
            if self.process.returncode == 0:
                self.status = TaskStatus.COMPLETED
                logger.info("[Task %s] 任务执行完成", self.task_id)
            else:
                self.status = TaskStatus.FAILED
                self.error_message = stderr
                logger.error("[Task %s] 任务执行失败, returncode=%d, stderr=%s", 
                           self.task_id, self.process.returncode, stderr)
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
                   url: str = None, token: str = None, user: str = None) -> Optional[str]:
        """创建新任务"""
        # 检查优化器是否存在（锁外执行，不涉及共享状态修改）
        if not optimizer_manager.validate_optimizer(airline, optimizer_type):
            logger.warning("创建任务失败: 航司 %s 的优化器 %s 不可用", airline, optimizer_type)
            return None
        
        with self.lock:
            # 并发数检查在锁内，保证原子性
            local_running_count = len([t for t in self.tasks.values() if t.status == TaskStatus.RUNNING])
            if local_running_count >= self.max_concurrent:
                logger.warning("创建任务失败: 已达最大并发数 %d", self.max_concurrent)
                return None
            
            task_id = str(uuid.uuid4())
            task = Task(task_id, airline, optimizer_type, parameters, url, token, user)
            self.tasks[task_id] = task
            
            if airline not in self.airline_tasks:
                self.airline_tasks[airline] = []
            self.airline_tasks[airline].append(task_id)
        
        logger.info("任务创建成功: task_id=%s, airline=%s, type=%s", task_id, airline, optimizer_type)
        return task_id
    
    def start_task(self, task_id: str) -> bool:
        """启动任务"""
        with self.lock:
            task = self.tasks.get(task_id)
            if not task:
                task_data = redis_manager.get_task(task_id)
                if task_data:
                    logger.warning("任务 %s 在其他服务器上，无法在本地启动", task_id)
                return False
            
            if task.status != TaskStatus.PENDING:
                return False
            
            local_running_count = len([t for t in self.tasks.values() if t.status == TaskStatus.RUNNING])
            if local_running_count >= self.max_concurrent:
                return False
        
        # 在锁外启动任务
        return task.start()
    
    def stop_task(self, task_id: str) -> bool:
        """停止任务"""
        # 在锁内仅获取task引用，在锁外执行stop（避免锁内等待进程）
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
