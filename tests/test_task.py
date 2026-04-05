import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import time
from src.tasks.task_manager import task_manager, TaskStatus


class TestTaskManager:
    """任务调度模块测试"""

    def test_create_task(self):
        """测试创建任务"""
        task_id = task_manager.create_task("F8", "PO", {"scenarioId": "123"})
        assert task_id is not None
        assert isinstance(task_id, str)

    def test_create_task_with_url_and_token(self):
        """测试创建带URL和Token的任务"""
        task_id = task_manager.create_task(
            "F8", "PO", {"scenarioId": "456"},
            url="http://localhost", token="test_token", user="test_user"
        )
        assert task_id is not None
        task = task_manager.get_task(task_id)
        assert task is not None
        assert task.url == "http://localhost"
        assert task.token == "test_token"
        assert task.user == "test_user"

    def test_create_task_invalid_optimizer(self):
        """测试创建不存在的优化器类型任务"""
        task_id = task_manager.create_task("F8", "INVALID")
        assert task_id is None

    def test_create_task_invalid_airline(self):
        """测试创建不存在航司的任务"""
        task_id = task_manager.create_task("INVALID", "PO")
        assert task_id is None

    def test_get_task(self):
        """测试获取任务"""
        task_id = task_manager.create_task("F8", "RO", {"scenarioId": "789"})
        assert task_id is not None
        task = task_manager.get_task(task_id)
        assert task is not None
        assert task.task_id == task_id
        assert task.airline == "F8"
        assert task.optimizer_type == "RO"

    def test_get_task_not_found(self):
        """测试获取不存在的任务"""
        task = task_manager.get_task("non_existent_task_id")
        assert task is None

    def test_task_initial_status(self):
        """测试任务初始状态"""
        task_id = task_manager.create_task("F8", "TO", {"scenarioId": "101"})
        assert task_id is not None
        task = task_manager.get_task(task_id)
        assert task is not None
        assert task.get_status() == "pending"
        assert task.get_progress() == 0

    def test_get_all_tasks(self):
        """测试获取所有任务"""
        all_tasks = task_manager.get_all_tasks("F8")
        assert isinstance(all_tasks, list)

    def test_get_running_tasks(self):
        """测试获取运行中任务"""
        running_tasks = task_manager.get_running_tasks("F8")
        assert isinstance(running_tasks, list)

    def test_create_rule_task(self):
        """测试创建Rule类型任务"""
        task_id = task_manager.create_task("F8", "Rule", {
            "category": "change_flight",
            "scenarioId": "0",
            "fltId": "1,2,3",
            "division": "C"
        })
        assert task_id is not None
        task = task_manager.get_task(task_id)
        assert task is not None
        assert task.optimizer_type == "Rule"

    def test_cleanup_tasks(self):
        """测试清理任务"""
        # cleanup_tasks应该不会出错
        task_manager.cleanup_tasks()
