import os
import uuid
import logging
from abc import ABC, abstractmethod
from typing import Dict, Optional, List
from datetime import datetime
from src.config.config import config_manager
from src.exceptions import OptimizerNotFoundError

logger = logging.getLogger(__name__)


class BaseOptimizer(ABC):
    """优化器基类 — 策略模式接口"""

    def __init__(self, airline: str, optimizer_type: str):
        self.airline = airline
        self.optimizer_type = optimizer_type
        self.config = config_manager.get_optimizer_config(airline, optimizer_type)
        self.platform = "windows" if os.name == "nt" else "linux"

    @abstractmethod
    def get_executable_path(self, parameters: dict = None) -> Optional[str]:
        """获取优化器可执行文件路径"""
        pass

    @abstractmethod
    def get_name(self, parameters: dict = None) -> str:
        """获取优化器名称"""
        pass

    @abstractmethod
    def build_dir_name(self, parameters: dict, task_id: str, timestamp: str) -> str:
        """构建任务工作目录名称"""
        pass

    def is_valid(self) -> bool:
        """检��优化器是否有效"""
        return self.config is not None

    def validate(self) -> bool:
        """验证优化器是否可用"""
        return self.is_valid()


class StandardOptimizer(BaseOptimizer):
    """PO/RO/TO 标准优化器"""

    def get_executable_path(self, parameters: dict = None) -> Optional[str]:
        if not self.config:
            return None
        if self.platform == "windows":
            return self.config.windows.path
        return self.config.linux.path

    def get_name(self, parameters: dict = None) -> str:
        if self.config and hasattr(self.config, 'name'):
            return self.config.name
        return self.optimizer_type

    def build_dir_name(self, parameters: dict, task_id: str, timestamp: str) -> str:
        scenario_id = parameters.get("scenarioId", "unknown")
        return f"{self.optimizer_type}_{scenario_id}_{timestamp}_{task_id}"


class RuleOptimizer(BaseOptimizer):
    """Rule 规则优化器"""

    def get_executable_path(self, parameters: dict = None) -> Optional[str]:
        if not self.config or not parameters:
            return None
        category = parameters.get("category")
        if not category or category not in self.config.categories:
            return None
        category_config = self.config.categories[category]
        if self.platform == "windows":
            return category_config.windows.path
        return category_config.linux.path

    def get_name(self, parameters: dict = None) -> str:
        if self.config and parameters:
            category = parameters.get("category")
            if category and category in self.config.categories:
                return self.config.categories[category].name
        return "Rule Optimizer"

    def build_dir_name(self, parameters: dict, task_id: str, timestamp: str) -> str:
        category = parameters.get("category", "unknown")
        return f"{category}_{timestamp}_{task_id}"


def _create_optimizer(airline: str, optimizer_type: str) -> BaseOptimizer:
    """工厂方法：根据类型创建对应的优化器实例"""
    if optimizer_type == "Rule":
        return RuleOptimizer(airline, optimizer_type)
    return StandardOptimizer(airline, optimizer_type)


class OptimizerManager:
    def __init__(self):
        self.optimizers: Dict[str, Dict[str, BaseOptimizer]] = {}  # airline -> optimizer_type -> Optimizer
        self._register_optimizers()

    def _register_optimizers(self):
        """注册所有优化器"""
        optimizer_types = ["PO", "RO", "TO", "Rule"]
        airlines = list(config_manager.get_config().airlines.keys())

        for airline in airlines:
            self.optimizers[airline] = {}
            for opt_type in optimizer_types:
                optimizer = _create_optimizer(airline, opt_type)
                if optimizer.is_valid():
                    self.optimizers[airline][opt_type] = optimizer

    def get_optimizer(self, airline: str, optimizer_type: str) -> Optional[BaseOptimizer]:
        """获取指定航司指定类型的优化器"""
        if airline not in self.optimizers:
            return None
        return self.optimizers[airline].get(optimizer_type)

    def get_all_optimizers(self, airline: str) -> List[str]:
        """获取指定航司所有可用的优化器类型"""
        if airline not in self.optimizers:
            return []
        return list(self.optimizers[airline].keys())

    def prepare_working_dir(self, airline: str, optimizer_type: str, parameters: dict = None, task_id: str = None) -> Optional[str]:
        """为优化器准备工作目录"""
        working_dir = config_manager.get_config().paths.working_dir
        parameters = parameters or {}
        task_id = task_id or str(uuid.uuid4())[:8]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 创建航司特定的工作目录
        airline_working_dir = os.path.join(working_dir, airline)
        os.makedirs(airline_working_dir, exist_ok=True)

        # 通过优化器策略构建目录名
        optimizer = self.get_optimizer(airline, optimizer_type)
        if optimizer:
            dir_name = optimizer.build_dir_name(parameters, task_id, timestamp)
        else:
            dir_name = f"{optimizer_type}_{timestamp}_{task_id}"

        task_dir = os.path.join(airline_working_dir, dir_name)
        os.makedirs(task_dir, exist_ok=True)

        return task_dir

    def validate_optimizer(self, airline: str, optimizer_type: str) -> bool:
        """验证优化器是否可用"""
        optimizer = self.get_optimizer(airline, optimizer_type)
        if not optimizer:
            return False
        return optimizer.validate()


# 全局优化器管理器实例
optimizer_manager = OptimizerManager()
