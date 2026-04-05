import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from src.optimizers.optimizer_manager import optimizer_manager


class TestOptimizerManager:
    """优化器管理模块测试"""

    def test_get_all_optimizers_f8(self):
        """测试获取F8航司的所有优化器"""
        optimizers = optimizer_manager.get_all_optimizers("F8")
        assert isinstance(optimizers, list)
        assert "PO" in optimizers
        assert "RO" in optimizers
        assert "TO" in optimizers
        assert "Rule" in optimizers

    def test_get_all_optimizers_br(self):
        """测试获取BR航司的所有优化器"""
        optimizers = optimizer_manager.get_all_optimizers("BR")
        assert isinstance(optimizers, list)
        assert len(optimizers) > 0

    def test_get_all_optimizers_invalid_airline(self):
        """测试获取不存在航司的优化器"""
        optimizers = optimizer_manager.get_all_optimizers("INVALID")
        assert optimizers == []

    def test_get_optimizer(self):
        """测试获取单个优化器"""
        for opt_type in ["PO", "RO", "TO", "Rule"]:
            optimizer = optimizer_manager.get_optimizer("F8", opt_type)
            assert optimizer is not None
            assert optimizer.is_valid()

    def test_get_optimizer_invalid_type(self):
        """测试获取不存在的优化器类型"""
        optimizer = optimizer_manager.get_optimizer("F8", "INVALID")
        assert optimizer is None

    def test_get_optimizer_invalid_airline(self):
        """测试获取不存在航司的优化器"""
        optimizer = optimizer_manager.get_optimizer("INVALID", "PO")
        assert optimizer is None

    def test_optimizer_executable_path(self):
        """测试优化器可执行文件路径"""
        optimizer = optimizer_manager.get_optimizer("F8", "PO")
        assert optimizer is not None
        path = optimizer.get_executable_path()
        assert path is not None
        assert isinstance(path, str)

    def test_rule_optimizer_executable_path(self):
        """测试Rule优化器可执行文件路径（应为None，因为有categories）"""
        optimizer = optimizer_manager.get_optimizer("F8", "Rule")
        assert optimizer is not None
        path = optimizer.get_executable_path()
        assert path is None  # Rule类型返回None

    def test_optimizer_name(self):
        """测试优化器名称"""
        optimizer = optimizer_manager.get_optimizer("F8", "PO")
        assert optimizer is not None
        name = optimizer.get_name()
        assert name == "Pairing Optimizer"

    def test_prepare_working_dir(self):
        """测试工作目录准备"""
        work_dir = optimizer_manager.prepare_working_dir(
            "F8", "PO", {"scenarioId": "123"}, "test1234"
        )
        assert work_dir is not None
        assert os.path.exists(work_dir)
        assert "PO_123_" in work_dir
        # 清理
        os.rmdir(work_dir)

    def test_prepare_working_dir_rule(self):
        """测试Rule类型工作目录准备"""
        work_dir = optimizer_manager.prepare_working_dir(
            "F8", "Rule", {"category": "manday"}, "test5678"
        )
        assert work_dir is not None
        assert os.path.exists(work_dir)
        assert "manday_" in work_dir
        # 清理
        os.rmdir(work_dir)

    def test_validate_optimizer(self):
        """测试优化器验证"""
        for opt_type in ["PO", "RO", "TO", "Rule"]:
            is_valid = optimizer_manager.validate_optimizer("F8", opt_type)
            assert is_valid is True

    def test_validate_optimizer_invalid(self):
        """测试验证不存在的优化器"""
        is_valid = optimizer_manager.validate_optimizer("F8", "INVALID")
        assert is_valid is False
