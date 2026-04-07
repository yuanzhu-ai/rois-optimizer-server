import os
import re
import sys
import yaml
from pydantic_settings import BaseSettings
from typing import Dict, Any, Optional


class OptimizerConfig(BaseSettings):
    path: str


class OptimizerURLConfig(BaseSettings):
    input: str
    output: str


class OptimizerOSConfig(BaseSettings):
    path: str


class RuleCategoryConfig(BaseSettings):
    name: str
    linux: OptimizerOSConfig
    windows: OptimizerOSConfig
    url: OptimizerURLConfig


class OptimizerTypeConfig(BaseSettings):
    name: str
    linux: OptimizerOSConfig
    windows: OptimizerOSConfig
    url: OptimizerURLConfig
    server_integration: bool = True  # true: server处理input/output传输; false: 优化器自身处理


class RuleOptimizerConfig(BaseSettings):
    categories: Dict[str, RuleCategoryConfig]
    server_integration: bool = True  # true: server处理input/output传输; false: 优化器自身处理


class OptimizersConfig(BaseSettings):
    PO: OptimizerTypeConfig
    RO: OptimizerTypeConfig
    TO: OptimizerTypeConfig
    Rule: RuleOptimizerConfig


class AirlineConfig(BaseSettings):
    optimizers: OptimizersConfig


class CorsConfig(BaseSettings):
    allow_origins: list = ["*"]  # 生产环境应配置为具体域名列表
    allow_methods: list = ["GET", "POST"]
    allow_headers: list = ["X-Airline", "X-API-Key", "Authorization", "Content-Type"]


class ServerConfig(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True
    cors: CorsConfig = CorsConfig()


class APIKeyConfig(BaseSettings):
    enabled: bool = False
    key: str = "your_api_key_here"


class BearerTokenConfig(BaseSettings):
    enabled: bool = False
    token: str = "your_bearer_token_here"


class AirlineAuthConfig(BaseSettings):
    api_key: str = ""
    bearer_token: str = ""


class JWTConfig(BaseSettings):
    enabled: bool = False
    secret: str = ""  # 与 Live Server 共享的 JWT 签名密钥
    algorithm: str = "HS256"
    verify_exp: bool = True  # 是否校验过期时间


class RateLimitConfig(BaseSettings):
    enabled: bool = False
    rate: str = "15/minute"  # 限流速率，格式: "次数/时间单位"


class AuthConfig(BaseSettings):
    enabled: bool = False
    jwt: JWTConfig = JWTConfig()
    api_key: APIKeyConfig = APIKeyConfig()
    bearer_token: BearerTokenConfig = BearerTokenConfig()
    airline_auth: Dict[str, AirlineAuthConfig] = {}
    rate_limit: RateLimitConfig = RateLimitConfig()


class PathsConfig(BaseSettings):
    working_dir: str = "./workspace"
    finished_dir: str = "./finished"
    archive_dir: str = "./archive"
    temp_dir: str = "./temp"


class FileManagementConfig(BaseSettings):
    archive_days: int = 1
    cleanup_days: int = 30


class RedisConfig(BaseSettings):
    enabled: bool = False
    host: str = "localhost"
    port: int = 6379
    password: Optional[str] = None
    db: int = 0
    task_ttl: int = 3600


class TasksConfig(BaseSettings):
    max_concurrent: int = 10
    timeout: int = 3600


class HttpClientConfig(BaseSettings):
    timeout: int = 600  # Live Server请求超时时间（秒），默认10分钟


class Config(BaseSettings):
    server: ServerConfig = ServerConfig()
    auth: AuthConfig = AuthConfig()
    paths: PathsConfig = PathsConfig()
    airlines: Dict[str, AirlineConfig]
    file_management: FileManagementConfig = FileManagementConfig()
    tasks: TasksConfig = TasksConfig()
    redis: RedisConfig = RedisConfig()
    http_client: HttpClientConfig = HttpClientConfig()


class ConfigManager:
    _instance = None
    _config = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
        return cls._instance

    @staticmethod
    def _resolve_env_vars(data):
        """递归解析配置值中的环境变量引用

        支持格式: ${ENV_VAR_NAME:default_value} 或 ${ENV_VAR_NAME}
        """
        if isinstance(data, str):
            pattern = r'\$\{([^}:]+)(?::([^}]*))?\}'
            def replacer(match):
                env_name = match.group(1)
                default_value = match.group(2) if match.group(2) is not None else match.group(0)
                return os.environ.get(env_name, default_value)
            return re.sub(pattern, replacer, data)
        elif isinstance(data, dict):
            return {k: ConfigManager._resolve_env_vars(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [ConfigManager._resolve_env_vars(item) for item in data]
        return data

    def load_config(self, config_path: str = None):
        """加载配置文件

        查找顺序：
          1. 显式参数
          2. 环境变量 ROIS_CONFIG_PATH
          3. 冻结模式（PyInstaller）：可执行文件所在目录的 config.yaml
             非冻结模式：src/config/config.yaml（开发模式默认）
        """
        if config_path is None:
            config_path = os.environ.get("ROIS_CONFIG_PATH")
        if config_path is None:
            if getattr(sys, "frozen", False):
                base = os.path.dirname(os.path.abspath(sys.executable))
            else:
                base = os.path.dirname(__file__)
            config_path = os.path.join(base, "config.yaml")

        import logging
        _logger = logging.getLogger(__name__)

        if not os.path.exists(config_path):
            # 如果配置文件不存在，使用默认配置
            _logger.warning("配置文件不存在: %s，将回退到内置默认配置（config.yaml.example）", config_path)
            self._config = self._create_default_config()
            return self._config

        _logger.info("加载配置文件: %s", config_path)
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)

        # 解析环境变量引用
        config_data = self._resolve_env_vars(config_data)

        self._config = Config(**config_data)
        return self._config

    def _create_default_config(self):
        """创建默认配置 — 从 config.yaml.example 加载，避免硬编码重复"""
        import logging
        _logger = logging.getLogger(__name__)

        # 尝试从 config.yaml.example 加载默认配置
        example_path = os.path.join(os.path.dirname(__file__), "config.yaml.example")
        if os.path.exists(example_path):
            _logger.info("配置文件不存在，从 config.yaml.example 加载默认配置")
            with open(example_path, "r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f)
            config_data = self._resolve_env_vars(config_data)
            return Config(**config_data)

        # config.yaml.example 也不存在时，抛出明确错误
        raise FileNotFoundError(
            "未找到配置文件。请复制 src/config/config.yaml.example 为 src/config/config.yaml 并修改配置。"
        )

    def get_config(self) -> Config:
        """获取配置"""
        if self._config is None:
            self.load_config()
        return self._config

    def get_airline_config(self, airline: str) -> AirlineConfig:
        """获取航司配置"""
        config = self.get_config()
        if airline not in config.airlines:
            raise ValueError(f"航司 {airline} 未配置")
        return config.airlines[airline]

    def get_optimizer_config(self, airline: str, optimizer_type: str):
        """获取优化器配置"""
        airline_config = self.get_airline_config(airline)
        if optimizer_type == "PO":
            return airline_config.optimizers.PO
        elif optimizer_type == "RO":
            return airline_config.optimizers.RO
        elif optimizer_type == "TO":
            return airline_config.optimizers.TO
        elif optimizer_type == "Rule":
            return airline_config.optimizers.Rule
        else:
            raise ValueError(f"不支持的优化器类型: {optimizer_type}")

    def get_optimizer_name(self, airline: str, optimizer_type: str) -> str:
        """获取优化器名称"""
        config = self.get_optimizer_config(airline, optimizer_type)
        if optimizer_type == "Rule":
            return "Rule Optimizer"
        return config.name if hasattr(config, 'name') else optimizer_type


# 全局配置管理器实例
config_manager = ConfigManager()
