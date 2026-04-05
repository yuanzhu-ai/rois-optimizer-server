import logging
from fastapi import APIRouter, Depends, HTTPException
from src.tasks.task_manager import task_manager
from src.optimizers.optimizer_manager import optimizer_manager
from src.api.auth import verify_token, AuthContext
from src.api.models import (
    OptimizeStartRequest, TaskStartResponse, TaskStopResponse,
    TaskStatusResponse, TaskProgressResponse, SystemInfoResponse,
    OptimizersResponse, TaskListResponse
)
from src.version import get_version, GIT_COMMIT_ID, BUILD_TIMESTAMP, COMMIT_AUTHOR
from src.exceptions import (
    OptimizerNotFoundError, OptimizerExecutionError,
    TaskNotFoundError, TaskLimitError, TaskStateError,
    InputFetchError, OutputSubmitError,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# 优化任务管理接口

@router.post("/optimize/start", response_model=TaskStartResponse)
async def start_optimization(request: OptimizeStartRequest, auth: AuthContext = Depends(verify_token)):
    """启动优化任务"""
    airline = auth.airline

    # 验证优化器类型
    valid_types = ["PO", "RO", "TO", "Rule"]
    if request.type not in valid_types:
        raise HTTPException(status_code=400, detail=f"不支持的优化器类型: {request.type}，支持: {valid_types}")

    # Rule类型必须有category参数
    if request.type == "Rule" and "category" not in request.parameters:
        raise HTTPException(status_code=400, detail="Rule类型必须在parameters中指定category参数")

    # PO/RO/TO类型必须有scenarioId
    if request.type in ["PO", "RO", "TO"] and "scenarioId" not in request.parameters:
        raise HTTPException(status_code=400, detail=f"{request.type}类型必须在parameters中指定scenarioId参数")

    # 确定 Live Server token:
    # - JWT 模式: 自动使用 Header 中的 JWT 传递给 Live Server
    # - API Key 模式: 使用 body 中的 token 字段
    live_server_token = request.token
    if auth.auth_method == "jwt" and auth.jwt_token:
        live_server_token = auth.jwt_token

    # 确定用户名: JWT 优先，否则用 body 中的 user 字段
    user = auth.user or request.user

    logger.info("收到启动任务请求: airline=%s, type=%s, user=%s, auth=%s",
                airline, request.type, user, auth.auth_method)

    try:
        task_id = task_manager.create_task(airline, request.type, request.parameters, request.url, live_server_token, user)
        task_manager.start_task(task_id)
    except OptimizerNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except TaskLimitError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except (TaskStateError, TaskNotFoundError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except InputFetchError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except OptimizerExecutionError as e:
        raise HTTPException(status_code=500, detail=str(e))

    return TaskStartResponse(task_id=task_id, status="started")

@router.post("/optimize/stop/{task_id}", response_model=TaskStopResponse)
async def stop_optimization(task_id: str, auth: AuthContext = Depends(verify_token)):
    """停止优化任务"""
    success = task_manager.stop_task(task_id)
    if not success:
        raise HTTPException(status_code=400, detail="停止任务失败，任务可能不存在或未在运行")

    return TaskStopResponse(task_id=task_id, status="stopped")

@router.get("/optimize/status/{task_id}", response_model=TaskStatusResponse)
async def get_optimization_status(task_id: str, auth: AuthContext = Depends(verify_token)):
    """查询优化任务状态"""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    return TaskStatusResponse(
        task_id=task_id,
        status=task.get_status(),
        airline=task.airline,
        optimizer_type=task.optimizer_type,
        error_message=task.error_message
    )

@router.get("/optimize/progress/{task_id}", response_model=TaskProgressResponse)
async def get_optimization_progress(task_id: str, auth: AuthContext = Depends(verify_token)):
    """查询优化任务进度"""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    return TaskProgressResponse(
        task_id=task_id,
        progress=task.get_progress(),
        status=task.get_status(),
        airline=task.airline
    )

# 系统管理接口

@router.get("/system/info", response_model=SystemInfoResponse)
async def get_system_info(auth: AuthContext = Depends(verify_token)):
    """获取系统信息"""
    return SystemInfoResponse(
        service="优化引擎调度工具",
        version=get_version(),
        git_commit_id=GIT_COMMIT_ID,
        commit_author=COMMIT_AUTHOR,
        build_timestamp=BUILD_TIMESTAMP,
        status="running"
    )

@router.get("/optimizers", response_model=OptimizersResponse)
async def get_optimizers(auth: AuthContext = Depends(verify_token)):
    """获取优化器列表"""
    optimizers = optimizer_manager.get_all_optimizers(auth.airline)
    return OptimizersResponse(optimizers=optimizers)

@router.get("/tasks/running", response_model=TaskListResponse)
async def get_running_tasks(auth: AuthContext = Depends(verify_token)):
    """获取运行中任务"""
    running_tasks = task_manager.get_running_tasks(auth.airline)
    return TaskListResponse(tasks=running_tasks)

@router.get("/tasks/all", response_model=TaskListResponse)
async def get_all_tasks(auth: AuthContext = Depends(verify_token)):
    """获取所有任务"""
    all_tasks = task_manager.get_all_tasks(auth.airline)
    return TaskListResponse(tasks=all_tasks)
