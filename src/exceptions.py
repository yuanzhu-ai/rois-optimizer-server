"""
统一异常定义模块
"""


class OptimizerServerError(Exception):
    """优化器服务基础异常"""
    pass


class ConfigError(OptimizerServerError):
    """配置相关异常"""
    pass


class OptimizerError(OptimizerServerError):
    """优化器相关异常"""
    pass


class OptimizerNotFoundError(OptimizerError):
    """优化器未找到"""
    pass


class OptimizerExecutionError(OptimizerError):
    """优化器执行异常"""
    pass


class TaskError(OptimizerServerError):
    """任务相关异常"""
    pass


class TaskNotFoundError(TaskError):
    """任务未找到"""
    pass


class TaskLimitError(TaskError):
    """任务并发数超限"""
    pass


class TaskStateError(TaskError):
    """任务状态异常"""
    pass


class FileError(OptimizerServerError):
    """文件操作异常"""
    pass


class InputFetchError(FileError):
    """输入文件获取异常"""
    pass


class OutputSubmitError(FileError):
    """输出文件提交异常"""
    pass


class LiveServerError(OptimizerServerError):
    """Live Server 通信异常"""
    pass


class AuthenticationError(OptimizerServerError):
    """认证异常"""
    pass
