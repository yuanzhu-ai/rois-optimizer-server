"""
API 请求和响应模型定义
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List


# ===== 请求模型 =====

class OptimizeStartRequest(BaseModel):
    """启动优化任务请求"""
    airline: str = Field(..., min_length=2, max_length=10, description="航司二字码")
    type: str = Field(..., min_length=1, max_length=20, description="优化器类型: PO/RO/TO/Rule")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="优化参数")
    url: Optional[str] = Field(None, description="Live Server基础URL")
    token: Optional[str] = Field(None, description="Live Server认证Token")
    user: Optional[str] = Field(None, max_length=100, description="用户ID")


# ===== 响应模型 =====

class TaskStartResponse(BaseModel):
    """启动任务响应"""
    task_id: str
    status: str


class TaskStopResponse(BaseModel):
    """停止任务响应"""
    task_id: str
    status: str


class TaskStatusResponse(BaseModel):
    """任务状态响应"""
    task_id: str
    status: str
    airline: str
    optimizer_type: str
    error_message: Optional[str] = None


class TaskProgressResponse(BaseModel):
    """任务进度响应"""
    task_id: str
    progress: int
    status: str
    airline: str


class SystemInfoResponse(BaseModel):
    """系统信息响应"""
    service: str
    version: str
    git_commit_id: str
    commit_author: str
    build_timestamp: str
    status: str


class OptimizersResponse(BaseModel):
    """优化器列表响应"""
    optimizers: List[str]


class TaskInfo(BaseModel):
    """任务信息"""
    task_id: str
    airline: str
    optimizer_type: str
    status: str
    progress: int
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    error_message: Optional[str] = None


class TaskListResponse(BaseModel):
    """任务列表响应"""
    tasks: List[TaskInfo]


class ErrorResponse(BaseModel):
    """错误响应"""
    detail: str
