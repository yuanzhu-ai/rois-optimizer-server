import os
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


class ServerConfig(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True


class APIKeyConfig(BaseSettings):
    enabled: bool = False
    key: str = "your_api_key_here"


class BearerTokenConfig(BaseSettings):
    enabled: bool = False
    token: str = "your_bearer_token_here"


class AirlineAuthConfig(BaseSettings):
    api_key: str = ""
    bearer_token: str = ""


class AuthConfig(BaseSettings):
    enabled: bool = False
    api_key: APIKeyConfig = APIKeyConfig()
    bearer_token: BearerTokenConfig = BearerTokenConfig()
    airline_auth: Dict[str, AirlineAuthConfig] = {}


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

    def load_config(self, config_path: str = None):
        """加载配置文件"""
        if config_path is None:
            # 默认配置文件路径
            config_path = os.path.join(
                os.path.dirname(__file__), "config.yaml"
            )

        if not os.path.exists(config_path):
            # 如果配置文件不存在，使用默认配置
            self._config = self._create_default_config()
            return self._config

        with open(config_path, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)

        self._config = Config(**config_data)
        return self._config

    def _create_default_config(self):
        """创建默认配置"""
        return Config(
            airlines={
                "F8": AirlineConfig(
                    optimizers=OptimizersConfig(
                        PO=OptimizerTypeConfig(
                            name="Pairing Optimizer",
                            linux=OptimizerOSConfig(path="./F8/po.sh"),
                            windows=OptimizerOSConfig(path="./F8/po.bat"),
                            url=OptimizerURLConfig(
                                input="/api/orengine/po/comptxt",
                                output="/api/orengine/po/solution"
                            ),
                            server_integration=True
                        ),
                        RO=OptimizerTypeConfig(
                            name="Roster Optimizer",
                            linux=OptimizerOSConfig(path="./F8/ro.sh"),
                            windows=OptimizerOSConfig(path="./F8/ro.bat"),
                            url=OptimizerURLConfig(
                                input="/api/orengine/ro/comptxt",
                                output="/api/orengine/ro/solution"
                            ),
                            server_integration=True
                        ),
                        TO=OptimizerTypeConfig(
                            name="Training Optimizer",
                            linux=OptimizerOSConfig(path="./F8/to.sh"),
                            windows=OptimizerOSConfig(path="./F8/to.bat"),
                            url=OptimizerURLConfig(
                                input="/api/orengine/to/comptxt",
                                output="/api/orengine/to/solution"
                            ),
                            server_integration=True
                        ),
                        Rule=RuleOptimizerConfig(
                            categories={
                                "change_flight": RuleCategoryConfig(
                                    name="Change Flight Rule",
                                    linux=OptimizerOSConfig(path="./F8/rule_change_flight.sh"),
                                    windows=OptimizerOSConfig(path="./F8/rule_change_flight.bat"),
                                    url=OptimizerURLConfig(
                                        input="/api/orengine/byFlight/comptxt",
                                        output="/api/orengine/byFlight/save/csv"
                                    )
                                ),
                                "manday": RuleCategoryConfig(
                                    name="Manday Rule",
                                    linux=OptimizerOSConfig(path="./F8/rule_manday.sh"),
                                    windows=OptimizerOSConfig(path="./F8/rule_manday.bat"),
                                    url=OptimizerURLConfig(
                                        input="/api/orengine/ro/partial/comptxt",
                                        output="/api/crewMandayFd/partlySave/csv/comp"
                                    )
                                ),
                                "manday_byCrew": RuleCategoryConfig(
                                    name="Manday by Crew Rule",
                                    linux=OptimizerOSConfig(path="./F8/rule_manday_byCrew.sh"),
                                    windows=OptimizerOSConfig(path="./F8/rule_manday_byCrew.bat"),
                                    url=OptimizerURLConfig(
                                        input="/api/orengine/byCrew/comptxt",
                                        output="/api/crewMandayFd/partlySave/csv/comp"
                                    )
                                )
                            },
                            server_integration=True
                        )
                    )
                ),
                "BR": AirlineConfig(
                    optimizers=OptimizersConfig(
                        PO=OptimizerTypeConfig(
                            name="Pairing Optimizer",
                            linux=OptimizerOSConfig(path="./BR/po.sh"),
                            windows=OptimizerOSConfig(path="./BR/po.bat"),
                            url=OptimizerURLConfig(
                                input="/api/orengine/po/comptxt",
                                output="/api/orengine/po/solution"
                            ),
                            server_integration=True
                        ),
                        RO=OptimizerTypeConfig(
                            name="Roster Optimizer",
                            linux=OptimizerOSConfig(path="./BR/ro.sh"),
                            windows=OptimizerOSConfig(path="./BR/ro.bat"),
                            url=OptimizerURLConfig(
                                input="/api/orengine/ro/comptxt",
                                output="/api/orengine/ro/solution"
                            ),
                            server_integration=True
                        ),
                        TO=OptimizerTypeConfig(
                            name="Training Optimizer",
                            linux=OptimizerOSConfig(path="./BR/to.sh"),
                            windows=OptimizerOSConfig(path="./BR/to.bat"),
                            url=OptimizerURLConfig(
                                input="/api/orengine/to/comptxt",
                                output="/api/orengine/to/solution"
                            ),
                            server_integration=True
                        ),
                        Rule=RuleOptimizerConfig(
                            categories={
                                "change_flight": RuleCategoryConfig(
                                    name="Change Flight Rule",
                                    linux=OptimizerOSConfig(path="./BR/rule_change_flight.sh"),
                                    windows=OptimizerOSConfig(path="./BR/rule_change_flight.bat"),
                                    url=OptimizerURLConfig(
                                        input="/api/orengine/byFlight/comptxt",
                                        output="/api/orengine/byFlight/save/csv"
                                    )
                                ),
                                "manday": RuleCategoryConfig(
                                    name="Manday Rule",
                                    linux=OptimizerOSConfig(path="./BR/rule_manday.sh"),
                                    windows=OptimizerOSConfig(path="./BR/rule_manday.bat"),
                                    url=OptimizerURLConfig(
                                        input="/api/orengine/ro/partial/comptxt",
                                        output="/api/crewMandayFd/partlySave/csv/comp"
                                    )
                                ),
                                "manday_byCrew": RuleCategoryConfig(
                                    name="Manday by Crew Rule",
                                    linux=OptimizerOSConfig(path="./BR/rule_manday_byCrew.sh"),
                                    windows=OptimizerOSConfig(path="./BR/rule_manday_byCrew.bat"),
                                    url=OptimizerURLConfig(
                                        input="/api/orengine/byCrew/comptxt",
                                        output="/api/crewMandayFd/partlySave/csv/comp"
                                    )
                                )
                            },
                            server_integration=True
                        )
                    )
                )
            }
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
