import redis
import json
import uuid
import logging
from typing import Optional, Dict, Any, List
from src.config.config import config_manager

logger = logging.getLogger(__name__)

# Redis key 前缀常量
KEY_PREFIX_TASK = "optimizer:task:"
KEY_SET_ALL_TASKS = "optimizer:tasks:all"
KEY_SET_RUNNING_TASKS = "optimizer:tasks:running"


class RedisManager:
    def __init__(self):
        self.redis_config = config_manager.get_config().redis
        self.redis_client = None
        self.server_id = str(uuid.uuid4())
        self._connected = False
        self._connect()

    def _connect(self):
        """连接到Redis（使用连接池）"""
        if not self.redis_config.enabled:
            return

        try:
            pool = redis.ConnectionPool(
                host=self.redis_config.host,
                port=self.redis_config.port,
                password=self.redis_config.password,
                db=self.redis_config.db,
                decode_responses=True,
                max_connections=20,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            self.redis_client = redis.Redis(connection_pool=pool)
            self.redis_client.ping()
            self._connected = True
            logger.info("Redis连接成功: %s:%s (连接池 max=20)", self.redis_config.host, self.redis_config.port)
        except Exception as e:
            logger.warning("Redis连接失败，将使用本地存储模式: %s", e)
            self.redis_client = None
            self._connected = False

    def is_connected(self) -> bool:
        """检查Redis连接状态"""
        if not self.redis_config.enabled or self.redis_client is None:
            return False

        # 周期性检测实际连接状态
        try:
            self.redis_client.ping()
            if not self._connected:
                logger.info("Redis连接已恢复")
                self._connected = True
            return True
        except Exception:
            if self._connected:
                logger.warning("Redis连接已断开，降级为本地存储模式")
                self._connected = False
            return False

    def get_server_id(self) -> str:
        """获取服务器ID"""
        return self.server_id

    def set_task(self, task_id: str, task_data: Dict[str, Any]) -> bool:
        """设置任务数据"""
        if not self.is_connected():
            return False

        try:
            key = f"{KEY_PREFIX_TASK}{task_id}"
            pipe = self.redis_client.pipeline()
            pipe.setex(key, self.redis_config.task_ttl, json.dumps(task_data))
            # 维护任务 ID 集合索引
            pipe.sadd(KEY_SET_ALL_TASKS, task_id)
            if task_data.get('status') == 'running':
                pipe.sadd(KEY_SET_RUNNING_TASKS, task_id)
            else:
                pipe.srem(KEY_SET_RUNNING_TASKS, task_id)
            pipe.execute()
            return True
        except Exception as e:
            logger.error("Redis设置任务失败 [%s]: %s", task_id, e)
            return False

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务数据"""
        if not self.is_connected():
            return None

        try:
            key = f"{KEY_PREFIX_TASK}{task_id}"
            data = self.redis_client.get(key)
            if data:
                return json.loads(data)
            # key 过期了，从索引中清理
            self.redis_client.srem(KEY_SET_ALL_TASKS, task_id)
            self.redis_client.srem(KEY_SET_RUNNING_TASKS, task_id)
            return None
        except Exception as e:
            logger.error("Redis获取任务失败 [%s]: %s", task_id, e)
            return None

    def delete_task(self, task_id: str) -> bool:
        """删除任务数据"""
        if not self.is_connected():
            return False

        try:
            pipe = self.redis_client.pipeline()
            pipe.delete(f"{KEY_PREFIX_TASK}{task_id}")
            pipe.srem(KEY_SET_ALL_TASKS, task_id)
            pipe.srem(KEY_SET_RUNNING_TASKS, task_id)
            pipe.execute()
            return True
        except Exception as e:
            logger.error("Redis删除任务失败 [%s]: %s", task_id, e)
            return False

    def update_task_progress(self, task_id: str, progress: int) -> bool:
        """更新任务进度（增量更新，不重写全量）"""
        if not self.is_connected():
            return False

        try:
            key = f"{KEY_PREFIX_TASK}{task_id}"
            data = self.redis_client.get(key)
            if not data:
                return False

            task_data = json.loads(data)
            task_data['progress'] = progress
            # 保持原有 TTL 不变
            ttl = self.redis_client.ttl(key)
            if ttl > 0:
                self.redis_client.setex(key, ttl, json.dumps(task_data))
            else:
                self.redis_client.setex(key, self.redis_config.task_ttl, json.dumps(task_data))
            return True
        except Exception as e:
            logger.error("Redis更新任务进度失败 [%s]: %s", task_id, e)
            return False

    def update_task_status(self, task_id: str, status: str) -> bool:
        """更新任务状态"""
        if not self.is_connected():
            return False

        try:
            key = f"{KEY_PREFIX_TASK}{task_id}"
            data = self.redis_client.get(key)
            if not data:
                return False

            task_data = json.loads(data)
            task_data['status'] = status

            pipe = self.redis_client.pipeline()
            ttl = self.redis_client.ttl(key)
            if ttl > 0:
                pipe.setex(key, ttl, json.dumps(task_data))
            else:
                pipe.setex(key, self.redis_config.task_ttl, json.dumps(task_data))

            # 更新运行中任务索引
            if status == 'running':
                pipe.sadd(KEY_SET_RUNNING_TASKS, task_id)
            else:
                pipe.srem(KEY_SET_RUNNING_TASKS, task_id)
            pipe.execute()
            return True
        except Exception as e:
            logger.error("Redis更新任务状态失败 [%s]: %s", task_id, e)
            return False

    def get_all_tasks(self, airline: Optional[str] = None) -> List[Dict]:
        """获取所有任务（通过集合索引，避免 SCAN 全库）"""
        if not self.is_connected():
            return []

        try:
            task_ids = self.redis_client.smembers(KEY_SET_ALL_TASKS)
            if not task_ids:
                return []

            # 批量获取任务数据
            keys = [f"{KEY_PREFIX_TASK}{tid}" for tid in task_ids]
            values = self.redis_client.mget(keys)

            tasks = []
            expired_ids = []
            for tid, val in zip(task_ids, values):
                if val is None:
                    expired_ids.append(tid)
                    continue
                task = json.loads(val)
                if not airline or task.get('airline') == airline:
                    tasks.append(task)

            # 清理已过期的索引
            if expired_ids:
                pipe = self.redis_client.pipeline()
                for tid in expired_ids:
                    pipe.srem(KEY_SET_ALL_TASKS, tid)
                    pipe.srem(KEY_SET_RUNNING_TASKS, tid)
                pipe.execute()

            return tasks
        except Exception as e:
            logger.error("Redis获取所有任务失败: %s", e)
            return []

    def get_running_tasks(self, airline: Optional[str] = None) -> List[Dict]:
        """获取运行中任务（通过运行中任务索引）"""
        if not self.is_connected():
            return []

        try:
            task_ids = self.redis_client.smembers(KEY_SET_RUNNING_TASKS)
            if not task_ids:
                return []

            keys = [f"{KEY_PREFIX_TASK}{tid}" for tid in task_ids]
            values = self.redis_client.mget(keys)

            tasks = []
            expired_ids = []
            for tid, val in zip(task_ids, values):
                if val is None:
                    expired_ids.append(tid)
                    continue
                task = json.loads(val)
                # 双重校验状态
                if task.get('status') != 'running':
                    expired_ids.append(tid)
                    continue
                if not airline or task.get('airline') == airline:
                    tasks.append(task)

            if expired_ids:
                pipe = self.redis_client.pipeline()
                for tid in expired_ids:
                    pipe.srem(KEY_SET_RUNNING_TASKS, tid)
                pipe.execute()

            return tasks
        except Exception as e:
            logger.error("Redis获取运行中任务失败: %s", e)
            return []

    def publish_task_event(self, task_id: str, event_type: str, data: Any) -> bool:
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
