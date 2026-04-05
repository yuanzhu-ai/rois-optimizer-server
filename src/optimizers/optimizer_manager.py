import os
import uuid
from typing import Dict, Optional, List
from src.config.config import config_manager


class Optimizer:
    def __init__(self, airline: str, optimizer_type: str):
        self.airline = airline
        self.optimizer_type = optimizer_type
        self.config = config_manager.get_optimizer_config(airline, optimizer_type)
        self.name = config_manager.get_optimizer_name(airline, optimizer_type)
        self.platform = "windows" if os.name == "nt" else "linux"
    
    def get_executable_path(self) -> Optional[str]:
        """获取优化器可执行文件路径"""
        if not self.config:
            return None
        
        # 根据平台返回对应的路径
        if self.optimizer_type == "Rule":
            # Rule优化器有categories，需要特殊处理
            return None
        else:
            # PO, RO, TO优化器
            if self.platform == "windows":
                return self.config.windows.path
            else:
                return self.config.linux.path
    
    def get_name(self) -> Optional[str]:
        """获取优化器名称"""
        return self.name
    
    def is_valid(self) -> bool:
        """检查优化器是否有效"""
        return self.config is not None


class OptimizerManager:
    def __init__(self):
        self.optimizers: Dict[str, Dict[str, Optimizer]] = {}  # airline -> optimizer_type -> Optimizer
        self._register_optimizers()
    
    def _register_optimizers(self):
        """注册所有优化器"""
        optimizer_types = ["PO", "RO", "TO", "Rule"]
        
        # 获取所有航司
        airlines = list(config_manager.get_config().airlines.keys())
        
        for airline in airlines:
            self.optimizers[airline] = {}
            for opt_type in optimizer_types:
                optimizer = Optimizer(airline, opt_type)
                if optimizer.is_valid():
                    self.optimizers[airline][opt_type] = optimizer
    
    def get_optimizer(self, airline: str, optimizer_type: str) -> Optional[Optimizer]:
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
        """为优化器准备工作目录
        
        命名规则:
        - PO/RO/TO: {type}_{scenarioId}_{timestamp}
        - Rule: {category}_{timestamp}
        """
        from datetime import datetime
        
        working_dir = config_manager.get_config().paths.working_dir
        parameters = parameters or {}
        task_id = task_id or str(uuid.uuid4())[:8]  # 使用短UUID
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 创建航司特定的工作目录
        airline_working_dir = os.path.join(working_dir, airline)
        os.makedirs(airline_working_dir, exist_ok=True)
        
        # 根据优化器类型构建目录名
        if optimizer_type == "Rule":
            # Rule类型使用category
            category = parameters.get("category", "unknown")
            dir_name = f"{category}_{timestamp}_{task_id}"
        else:
            # PO/RO/TO类型使用scenarioId
            scenario_id = parameters.get("scenarioId", "unknown")
            dir_name = f"{optimizer_type}_{scenario_id}_{timestamp}_{task_id}"
        
        # 创建任务特定的工作目录
        task_dir = os.path.join(airline_working_dir, dir_name)
        os.makedirs(task_dir, exist_ok=True)
        
        return task_dir
    
    def validate_optimizer(self, airline: str, optimizer_type: str) -> bool:
        """验证优化器是否可用"""
        optimizer = self.get_optimizer(airline, optimizer_type)
        if not optimizer:
            return False
        
        # Rule类型不需要检查可执行文件路径（它有categories）
        if optimizer_type == "Rule":
            return True
        
        # 检查可执行文件是否存在
        exec_path = optimizer.get_executable_path()
        if not exec_path:
            return False
        
        # 在实际环境中，这里应该检查文件是否存在且可执行
        # 但由于是示例配置，我们暂时返回True
        return True


# 全局优化器管理器实例
optimizer_manager = OptimizerManager()
