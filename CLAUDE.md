# CLAUDE.md — ROIS Optimizer Server

## 项目简介

FastAPI 优化引擎调度服务，管理 PO/RO/TO/Rule 四类优化器，支持多航司（BR/F8）、任务生命周期、文件归档、Live Server 集成。

## 技术栈

Python 3.8+ / FastAPI / Pydantic / PyJWT / slowapi / Redis(可选) / PyInstaller

## 常用命令

```bash
# 启动
python3 main.py
# 或
uvicorn main:app --host 0.0.0.0 --port 8000

# 测试（105 个）
python3 -m pytest tests/test_input_interface.py tests/test_output_interface.py tests/test_auth_and_errors.py tests/test_file_management.py tests/test_e2e_lifecycle.py tests/test_jwt_auth.py -v

# 构建可执行文件
./build.sh        # Linux
build.bat          # Windows
```

## 项目结构

```
main.py                          # 入口：FastAPI app + CORS + 限流 + 生命周期
config.yaml                      # 运行时配置（不提交，从 example 复制）
src/
  exceptions.py                  # 统一异常层次
  api/
    auth.py                      # 认证：JWT > API Key > Bearer Token + AuthContext
    routes.py                    # 8 个 API 端点
    models.py                    # Pydantic 请求/响应模型
  config/config.py               # 配置管理（单例 + 环境变量 ${VAR:default}）
  optimizers/optimizer_manager.py # 策略模式：BaseOptimizer / StandardOptimizer / RuleOptimizer
  tasks/task_manager.py          # 任务生命周期：创建→启动→监控→完成/失败/停止
  tasks/redis_manager.py         # Redis 分布式任务状态（可选）
  files/file_manager.py          # 文件移动/归档/清理
  utils/http_client.py           # Live Server HTTP 客户端
  utils/rule_request_builder.py  # Rule 请求体构建
tests/
  conftest.py                    # Mock Live Server + Mock 优化器脚本 + 测试 fixture
  test_input_interface.py        # 6 种优化器 input.gz 获取（19 个）
  test_output_interface.py       # 6 种优化器 output.gz 提交（17 个）
  test_e2e_lifecycle.py          # 端到端全流程 + 并发（22 个）
  test_auth_and_errors.py        # 认证 + 参数校验（21 个）
  test_jwt_auth.py               # JWT 专项测试（12 个）
  test_file_management.py        # 文件管理（14 个）
```

## 核心架构要点

- **认证三层优先级**：JWT(HS256 共享密钥) → API Key → 静态 Bearer Token
- **JWT 模式**：复用 Live Server 签发的 JWT，自动传递给 Live Server，body 不需要 token 字段
- **API Key 模式**：Live Server 服务间调用使用，无登录态场景
- **限流**：slowapi 按 X-Airline 维度，15 次/分钟（config.yaml 可配）
- **优化器策略模式**：`StandardOptimizer`(PO/RO/TO) 和 `RuleOptimizer` 继承 `BaseOptimizer`
- **任务执行链路**：input.gz 获取 → subprocess 执行优化器 → stdout 解析进度(PROGRESS:N) → output.gz 回传 → 文件归档
- **子进程安全**：独立线程读取 stdout/stderr 防死锁，monitor 线程等待进程 + join 读取线程
- **配置**：支持 `${ENV_VAR:default}` 环境变量语法，默认从 config.yaml.example 加载

## 环境变量

```bash
JWT_SECRET=xxx          # 与 Live Server 共享的 JWT 签名密钥
ROIS_API_KEY=xxx        # API Key（Live Server 调用时使用）
ROIS_BEARER_TOKEN=xxx   # 静态 Bearer Token（向后兼容）
```

## 详细文档索引

需要深入了解时按需加载：

- [API 接口文档](doc/documents/api_documentation.md) — 端点定义、请求/响应格式、认证示例
- [系统架构](doc/documents/system_architecture.md) — 分层架构、模块关系、分布式部署
- [认证方案](doc/documents/auth_design_proposal.md) — JWT 设计决策、认证流程、已实施状态
- [架构审查报告](doc/documents/architecture_review.md) — 问题清单、修复记录、优化路线图
- [部署指南](doc/documents/deployment_guide.md) — 环境准备、配置、启动、多机部署
- [需求文档](doc/documents/optimize_server_requirements.md) — 功能/非功能需求
- [实现计划](doc/documents/optimize_server_implementation_plan.md) — 10 个任务的开发计划
