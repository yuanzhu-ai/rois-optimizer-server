import redis
import json
import uuid
import logging
from typing import Optional, Dict, Any
from src.config.config import config_manager

logger = logging.getLogger(__name__)


class RedisManager:
    def __init__(self):
        self.redis_config = config_manager.get_config().redis
        self.redis_client = None
        self.server_id = str(uuid.uuid4())
        self._connect()
    
    def _connect(self):
        """连接到Redis"""
        if self.redis_config.enabled:
            try:
                self.redis_client = redis.Redis(
                    host=self.redis_config.host,
                    port=self.redis_config.port,
                    password=self.redis_config.password,
                    db=self.redis_config.db,
                    decode_responses=True
                )
                self.redis_client.ping()
                logger.info("Redis连接成功: %s:%s", self.redis_config.host, self.redis_config.port)
            except Exception as e:
                logger.warning("Redis连接失败，将使用本地存储模式: %s", e)
                self.redis_client = None
    
    def is_connected(self) -> bool:
        """检查Redis连接状态"""
        return self.redis_config.enabled and self.redis_client is not None
    
    def get_server_id(self) -> str:
        """获取服务器ID"""
        return self.server_id
    
    def set_task(self, task_id: str, task_data: Dict[str, Any]):
        """设置任务数据"""
        if not self.is_connected():
            return False
        
        try:
            key = f"task:{task_id}"
            self.redis_client.setex(
                key,
                self.redis_config.task_ttl,
                json.dumps(task_data)
            )
            return True
        except Exception as e:
            logger.error("Redis设置任务失败 [%s]: %s", task_id, e)
            return False
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务数据"""
        if not self.is_connected():
            return None
        
        try:
            key = f"task:{task_id}"
            data = self.redis_client.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            logger.error("Redis获取任务失败 [%s]: %s", task_id, e)
            return None
    
    def delete_task(self, task_id: str):
        """删除任务数据"""
        if not self.is_connected():
            return False
        
        try:
            key = f"task:{task_id}"
            self.redis_client.delete(key)
            return True
        except Exception as e:
            logger.error("Redis删除任务失败 [%s]: %s", task_id, e)
            return False
    
    def update_task_progress(self, task_id: str, progress: int):
        """更新任务进度"""
        if not self.is_connected():
            return False
        
        try:
            task_data = self.get_task(task_id)
            if task_data:
                task_data['progress'] = progress
                return self.set_task(task_id, task_data)
            return False
        except Exception as e:
            logger.error("Redis更新任务进度失败 [%s]: %s", task_id, e)
            return False
    
    def update_task_status(self, task_id: str, status: str):
        """更新任务状态"""
        if not self.is_connected():
            return False
        
        try:
            task_data = self.get_task(task_id)
            if task_data:
                task_data['status'] = status
                return self.set_task(task_id, task_data)
            return False
        except Exception as e:
            logger.error("Redis更新任务状态失败 [%s]: %s", task_id, e)
            return False
    
    def get_all_tasks(self, airline: Optional[str] = None) -> list:
        """获取所有任务"""
        if not self.is_connected():
            return []
        
        try:
            tasks = []
            cursor = 0
            while True:
                cursor, keys = self.redis_client.scan(cursor, match="task:*", count=100)
                for key in keys:
                    data = self.redis_client.get(key)
                    if data:
                        task = json.loads(data)
                        if not airline or task.get('airline') == airline:
                            tasks.append(task)
                if cursor == 0:
                    break
            return tasks
        except Exception as e:
            logger.error("Redis获取所有任务失败: %s", e)
            return []
    
    def get_running_tasks(self, airline: Optional[str] = None) -> list:
        """获取运行中任务"""
        if not self.is_connected():
            return []
        
        try:
            tasks = []
            cursor = 0
            while True:
                cursor, keys = self.redis_client.scan(cursor, match="task:*", count=100)
                for key in keys:
                    data = self.redis_client.get(key)
                    if data:
                        task = json.loads(data)
                        if task.get('status') == 'running':
                            if not airline or task.get('airline') == airline:
                                tasks.append(task)
                if cursor == 0:
                    break
            return tasks
        except Exception as e:
            logger.error("Redis获取运行中任务失败: %s", e)
            return []
    
    def publish_task_event(self, task_id: str, event_type: str, data: Any):
        """发布任务事件"""
        if not self.is_connected():
            return False
        
        try:
            channel = f"task:{task_id}:{event_type}"
            self.redis_client.publish(channel, json.dumps(data))
            return True
        except Exception as e:
            logger.error("Redis发布任务事件失败 [%s:%s]: %s", task_id, event_type, e)
            return False


# 全局Redis管理器实例
redis_manager = RedisManager()
