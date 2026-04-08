# 优化引擎调度工具 - 系统架构文档

## 1. 系统概述

优化引擎调度工具是一个轻量级的服务，用于统一管理和调度各种优化器（如PO、RO、TO、Rule等），支持多机部署，提供优化进度和状态的查询，以及支持优化器的启动和杀停。系统支持按航司配置不同的优化器版本，每个航司可以独立管理自己的优化任务。

## 2. 系统架构

### 2.1 架构层次

系统采用分层架构设计，主要分为以下几个层次：

1. **API层**：处理HTTP请求，提供RESTful接口
2. **业务逻辑层**：处理调度逻辑，管理优化任务
3. **执行层**：负责执行优化器，监控执行状态
4. **文件管理层**：处理文件的移动、压缩和清理
5. **配置管理层**：管理系统配置和优化器配置

### 2.2 模块结构

```
optimize-server/
├── main.py              # 应用入口
├── requirements.txt     # 依赖包
├── start.bat            # Windows启动脚本
├── start.sh             # Linux启动脚本
├── build.bat            # Windows编译脚本
├── build.sh             # Linux编译脚本
├── optimize_server.spec # PyInstaller配置文件
├── generate_git_properties.py # 版本信息生成脚本
├── src/
│   ├── api/             # API接口模块
│   │   ├── auth.py      # 认证中间件
│   │   └── routes.py    # API路由
│   ├── config/          # 配置管理模块
│   │   ├── config.py    # 配置管理
│   │   └── config.yaml.example # 配置文件示例
│   ├── files/           # 文件管理模块
│   │   └── file_manager.py # 文件管理
│   ├── optimizers/      # 优化器管理模块
│   │   └── optimizer_manager.py # 优化器管理
│   ├── tasks/           # 任务调度模块
│   │   ├── task_manager.py # 任务管理
│   │   └── redis_manager.py # Redis管理
│   ├── utils/           # 工具模块
│   │   ├── http_client.py # HTTP客户端（与Live Server通信）
│   │   └── rule_request_builder.py # Rule请求构建器
│   ├── scheduler/       # 调度模块
│   │   └── __init__.py
│   └── version.py       # 版本信息模块
├── tests/               # 测试模块（所有test*.py文件）
├── workspace/           # 工作目录（运行时创建）
│   └── {airline}/       # 航司工作目录
│       └── {task_dir}/  # 任务工作目录
├── finished/            # 完成文件目录（运行时创建）
├── archive/             # 归档目录（运行时创建）
└── temp/                # 临时目录（运行时创建）
```

### 2.3 核心模块

#### 2.3.1 配置管理模块
- **功能**：加载和解析配置文件，支持不同平台的配置适配，支持按航司配置优化器，启动时检查目录和文件存在性
- **核心类**：`ConfigManager`, `AirlineConfig`, `OptimizersConfig`
- **配置文件**：`config.yaml`
- **航司配置**：每个航司可以配置不同的优化器版本
- **目录检查**：启动时检查航司目录、优化器路径和文件是否存在，不存在则启动失败并给出明确错误信息

#### 2.3.2 优化器管理模块
- **功能**：管理不同类型的优化器，按航司管理优化器，准备执行环境
- **核心类**：`OptimizerManager`, `Optimizer`
- **航司支持**：根据航司获取对应的优化器配置

#### 2.3.3 任务调度模块
- **功能**：创建和管理任务，按航司管理任务，启动和停止任务，监控任务状态
- **核心类**：`TaskManager`, `Task`
- **任务状态**：pending, running, completed, failed, stopped
- **航司支持**：支持按航司查询任务状态和进度
- **分布式支持**：支持多机部署，使用Redis共享任务状态

#### 2.3.4 Redis管理模块
- **功能**：管理Redis连接，提供任务数据的分布式存储和同步
- **核心类**：`RedisManager`
- **任务同步**：支持任务状态和进度的实时同步
- **事件通知**：支持任务事件的发布和订阅

#### 2.3.5 文件管理模块
- **功能**：管理优化过程中产生的文件，包括移动、归档和清理
- **核心类**：`FileManager`
- **任务目录搬运**：`move_to_finished` 将整个任务工作目录（保留子目录结构）搬运至
  `finished/<airline>/<task_dir>`，支持 `suffix` 参数（如 `_failed`、`_stop`）
- **航司隔离归档**：`archive_files` 按 `archive/<airline>/<date>/` 组织归档；任务子目录
  打包为 `<task>.tar.gz` 保留内部结构，散文件单独 gzip
- **冲突处理**：目标命名冲突时追加时间戳 + 短 UUID，避免覆盖
- **遗留兼容**：`finished/` 顶层散文件落入 `archive/_legacy/<date>/` 不丢失

#### 2.3.6 API接口模块
- **功能**：提供RESTful API接口，处理HTTP请求
- **认证**：支持三种认证方式，按优先级依次尝试：
  1. **JWT认证（优先级1）**：基于HS256算法的JWT令牌验证，与Live Server共享密钥
  2. **API Key认证（优先级2）**：通过`X-API-Key`请求头传递，适用于服务间调用
  3. **Bearer Token静态认证（优先级3）**：通过`Authorization: Bearer <token>`请求头传递，用于简单场景
- **速率限制**：基于slowapi实现，默认每航司每分钟15次请求限制
- **路由**：优化任务管理接口和系统管理接口
- **航司支持**：所有接口都支持传入airline参数

#### 2.3.7 HTTP客户端模块
- **功能**：与 Live Server 进行 HTTP 通信，统一承担获取 input.gz 与回传 output.gz 的职责
- **核心类**：`LiveServerClient`, `create_live_server_client`
- **统一入口**：内部通过私有 `_post` 辅助集中处理 URL 构建、请求头、`timeout`、`verify`、
  legacy_ssl adapter 与异常包装；`get_input_data` / `submit_output_data` 均为其薄封装，
  确保所有对 Live Server 的请求行为一致
- **可配置超时**：支持通过 config.yaml 配置请求超时时间（默认 1200 秒 = 20 分钟）
- **TLS 兼容**：支持 `legacy_ssl`（OpenSSL SECLEVEL=1，兼容弱密钥/SHA1 证书）与
  `ssl_verify=false`（跳过自签名证书校验），两项配置对 input/output 两条链路生效
- **请求格式**：根据优化器类型自动选择请求数据格式（PO/RO/TO 发送纯整数，Rule 发送 JSON 对象）

## 3. 数据流

### 3.1 优化任务执行流程

1. **任务创建**：客户端通过API创建优化任务，传入airline、optimizer_type、parameters、url、token、user
2. **任务启动**：系统启动优化任务，准备工作目录（按航司组织）
3. **工作目录命名**：
   - **PO/RO/TO**: `{type}_{scenarioId}_{timestamp}_{taskId}`
     - 例如: `PO_3896_20260404_003315_2075d6f6`
   - **Rule**: `{category}_{timestamp}_{taskId}`
     - 例如: `manday_byCrew_20260404_003322_cbd11bbe`
4. **获取输入文件**：从Live Server获取input.gz文件
   - 使用调用方传入的url作为基础URL
   - 最终URL = `{url}{config中的input路径}`
   - 例如: `http://localhost/api/orengine/po/comptxt`
   - 使用调用方传入的token进行Live Server认证
   - **请求数据格式**：
     - **PO/RO/TO类型**：发送纯整数 `scenarioId`（例如：`3896`）
     - **Rule类型**：发送JSON对象（例如：`{"scenarioId": 3896, "category": "manday_byCrew", ...}`）
   - **超时设置**：默认20分钟（1200秒），可通过config.yaml调整
5. **执行优化**：执行优化器，监控执行状态和进度
6. **处理输出**：处理优化产生的输出文件
7. **回传结果**：向Live Server回传output.gz文件（使用调用方传入的URL和token）
8. **文件管理**：将文件移动至航司的Finished文件夹，然后归档和清理

### 3.2 API请求流程

1. **认证**：验证请求中的token
2. **参数验证**：验证请求参数，包括airline参数
3. **航司路由**：根据airline参数路由到对应的航司配置
4. **业务处理**：处理业务逻辑
5. **返回响应**：返回处理结果

## 4. 技术栈

- **语言**：Python 3.8+
- **Web框架**：FastAPI
- **配置管理**：PyYAML, Pydantic
- **任务管理**：多线程
- **分布式存储**：Redis
- **文件处理**：Python标准库
- **HTTP客户端**：Requests
- **打包工具**：PyInstaller
- **测试**：Pytest

## 5. 部署架构

### 5.1 单节点部署

- **服务器**：单台服务器
- **服务**：优化引擎调度工具服务
- **存储**：本地文件系统
- **航司目录**：每个航司有独立的优化器目录和文件目录

### 5.2 多节点部署

- **服务器**：多台服务器
- **负载均衡**：前端负载均衡器
- **服务**：优化引擎调度工具服务（多实例）
- **分布式存储**：Redis集群（用于任务状态同步）
- **文件存储**：共享存储或文件同步
- **航司目录**：每个航司的目录需要在所有节点上同步
- **任务同步**：通过Redis实现任务状态和进度的实时同步
- **事件通知**：通过Redis发布订阅机制实现任务事件通知

### 5.3 可执行文件部署

- **编译**：使用PyInstaller打包生成可执行文件
- **部署**：部署可执行文件和配置文件
- **版本信息**：编译时自动生成git.properties文件

## 6. 航司配置

### 6.1 配置结构

```yaml
# 服务器配置
server:
  host: 0.0.0.0
  port: 8000
  debug: true

# 认证配置
auth:
  enabled: false  # 是否启用认证
  # JWT认证（优先级1）：与Live Server共享密钥
  jwt:
    enabled: false  # 是否启用JWT认证
    secret: your_jwt_secret_here  # HS256共享密钥（与Live Server相同）
    algorithm: HS256  # 签名算法
  # API Key认证（优先级2）：服务间调用
  api_key:
    enabled: false  # 是否启用API Key认证
    key: your_api_key_here  # API Key值
  # Bearer Token静态认证（优先级3）
  bearer_token:
    enabled: false  # 是否启用Bearer Token认证
    token: your_bearer_token_here  # Bearer Token值
  # 速率限制配置
  rate_limit:
    enabled: true  # 是否启用速率限制
    requests_per_minute: 15  # 每航司每分钟最大请求数
  # 航司认证配置
  airline_auth:
    F8:
      api_key: f8_api_key_here  # F8航司API Key
      bearer_token: f8_bearer_token_here  # F8航司Bearer Token
    BR:
      api_key: br_api_key_here  # BR航司API Key
      bearer_token: br_bearer_token_here  # BR航司Bearer Token

# 文件路径配置
paths:
  working_dir: ./workspace
  finished_dir: ./finished
  archive_dir: ./archive
  temp_dir: ./temp

# 航司配置
airlines:
  F8:
    optimizers:
      PO:
        name: Pairing Optimizer
        server_integration: true  # true: server处理input/output传输; false: 优化器自身处理
        url:
          input: /api/orengine/po/comptxt
          output: /api/orengine/po/solution
        linux:
          path: ./F8/po.sh
        windows:
          path: ./F8/po.bat
      RO:
        name: Roster Optimizer
        server_integration: true  # true: server处理input/output传输; false: 优化器自身处理
        url:
          input: /api/orengine/ro/comptxt
          output: /api/orengine/ro/solution
        linux:
          path: ./F8/ro.sh
        windows:
          path: ./F8/ro.bat
      TO:
        name: Training Optimizer
        server_integration: true  # true: server处理input/output传输; false: 优化器自身处理
        url:
          input: /api/orengine/to/comptxt
          output: /api/orengine/to/solution
        linux:
          path: ./F8/to.sh
        windows:
          path: ./F8/to.bat
      Rule:
        server_integration: true  # true: server处理input/output传输; false: 优化器自身处理
        categories:
          change_flight:
            name: Change Flight Rule
            url:
              input: /api/orengine/byFlight/comptxt
              output: /api/orengine/byFlight/save/csv
            linux:
              path: ./F8/rule_change_flight.sh
            windows:
              path: ./F8/rule_change_flight.bat
          manday:
            name: Manday Rule
            url:
              input: /api/orengine/ro/partial/comptxt
              output: /api/crewMandayFd/partlySave/csv/comp
            linux:
              path: ./F8/rule_manday.sh
            windows:
              path: ./F8/rule_manday.bat
          manday_byCrew:
            name: Manday by Crew Rule
            url:
              input: /api/orengine/byCrew/comptxt
              output: /api/crewMandayFd/partlySave/csv/comp
            linux:
              path: ./F8/rule_manday_byCrew.sh
            windows:
              path: ./F8/rule_manday_byCrew.bat
  BR:
    optimizers:
      PO:
        name: Pairing Optimizer
        server_integration: true  # true: server处理input/output传输; false: 优化器自身处理
        url:
          input: /api/orengine/po/comptxt
          output: /api/orengine/po/solution
        linux:
          path: ./BR/po.sh
        windows:
          path: ./BR/po.bat
      RO:
        name: Roster Optimizer
        server_integration: true  # true: server处理input/output传输; false: 优化器自身处理
        url:
          input: /api/orengine/ro/comptxt
          output: /api/orengine/ro/solution
        linux:
          path: ./BR/ro.sh
        windows:
          path: ./BR/ro.bat
      TO:
        name: Training Optimizer
        server_integration: true  # true: server处理input/output传输; false: 优化器自身处理
        url:
          input: /api/orengine/to/comptxt
          output: /api/orengine/to/solution
        linux:
          path: ./BR/to.sh
        windows:
          path: ./BR/to.bat
      Rule:
        server_integration: true  # true: server处理input/output传输; false: 优化器自身处理
        categories:
          change_flight:
            name: Change Flight Rule
            url:
              input: /api/orengine/byFlight/comptxt
              output: /api/orengine/byFlight/save/csv
            linux:
              path: ./BR/rule_change_flight.sh
            windows:
              path: ./BR/rule_change_flight.bat
          manday:
            name: Manday Rule
            url:
              input: /api/orengine/ro/partial/comptxt
              output: /api/crewMandayFd/partlySave/csv/comp
            linux:
              path: ./BR/rule_manday.sh
            windows:
              path: ./BR/rule_manday.bat
          manday_byCrew:
            name: Manday by Crew Rule
            url:
              input: /api/orengine/byCrew/comptxt
              output: /api/crewMandayFd/partlySave/csv/comp
            linux:
              path: ./BR/rule_manday_byCrew.sh
            windows:
              path: ./BR/rule_manday_byCrew.bat

# 文件管理配置
file_management:
  archive_days: 1  # 隔天归档
  cleanup_days: 30  # 30天后清理

# 任务配置
tasks:
  max_concurrent: 10
  timeout: 3600  # 任务超时时间（秒）

# Redis配置
redis:
  enabled: false  # 是否启用Redis
  host: localhost  # Redis主机
  port: 6379  # Redis端口
  password: null  # Redis密码
  db: 0  # Redis数据库
  task_ttl: 3600  # 任务数据过期时间（秒）
```

### 6.2 目录结构

优化器二进制按航司隔离，运行时产物按航司分桶：

```
{airline}/
└── optimizers/        # 优化器可执行文件（按航司隔离）

finished/<airline>/<task_dir>/   # 任务完成后整体搬运的工作目录（保留子目录）
archive/<airline>/<date>/        # 按日归档：任务目录打包为 <task>.tar.gz，散文件单独 .gz
archive/_legacy/<date>/          # 兼容遗留 finished 顶层散文件的归档落点
```

### 6.3 任务集成模式

系统支持两种任务集成模式，通过每个航司的每种优化器类型配置下的 `server_integration` 参数控制（每个航司的每种优化引擎可以独立设置）：

#### 6.3.1 Server集成模式（server_integration: true）

- **适用场景**：新优化引擎，需要Server统一管理数据流
- **工作流程**：
  1. Server调用Live Server的input接口，获取input.gz文件
  2. Server调用优化器的sh/bat脚本执行优化
  3. 优化器生成output.gz文件
  4. Server调用Live Server的output接口，提交output.gz文件
  5. 数据保存成功，任务进度100%，状态为成功；否则失败

#### 6.3.2 优化器自集成模式（server_integration: false）

- **适用场景**：老优化引擎，优化器自身已经实现了数据流管理
- **工作流程**：
  1. 优化器自身调用Live Server的input接口，获取input.gz文件
  2. 优化器执行优化并生成output.gz文件
  3. 优化器自身调用Live Server的output接口，提交output.gz文件
  4. 数据保存成功，任务进度100%，状态为成功；否则失败
- **Server职责**：仅负责任务的启动、停止和状态监控，不干预数据流

### 6.4 API接口

所有API接口都支持airline参数：

- `POST /optimize/start`：启动优化任务，需要传入airline参数
- `GET /optimizers`：获取优化器列表，需要传入airline参数
- `GET /tasks/running`：获取运行中任务，支持按airline过滤
- `GET /tasks/all`：获取所有任务，支持按airline过滤

## 7. 扩展性

### 7.1 优化器扩展

- 支持添加新的优化器类型
- 通过配置文件配置新的优化器
- 每个航司可以配置不同的优化器版本

### 7.2 航司扩展

- 支持添加新的航司
- 在配置文件中添加航司配置
- 自动创建航司目录结构

### 7.3 功能扩展

- 支持添加新的API接口
- 支持集成新的外部系统

### 7.4 性能扩展

- 支持水平扩展，增加服务实例
- 支持调整并发任务数

## 8. 监控和维护

### 8.1 日志

- 系统日志：记录服务启动、停止、错误等信息
- 任务日志：记录任务执行状态和结果
- 航司日志：按航司记录操作日志

### 8.2 监控

- 服务状态监控
- 任务执行监控
- 资源使用监控
- 航司任务监控

### 8.3 维护

- 配置文件管理
- 依赖包更新
- 系统备份
- 航司目录管理

## 9. 安全考虑

### 9.1 认证和授权

系统支持三种认证方式，按优先级依次尝试，首个匹配即通过：

1. **JWT认证（优先级1）**
   - 使用HS256算法的共享密钥签名验证
   - 与Live Server复用相同的JWT密钥，实现单点登录
   - 从JWT payload中提取airline、user等信息
   - 通过`Authorization: Bearer <jwt_token>`请求头传递

2. **API Key认证（优先级2）**
   - 适用于Live Server等服务间调用场景
   - 通过`X-API-Key`请求头传递
   - 支持全局API Key和按航司API Key

3. **Bearer Token静态认证（优先级3）**
   - 简单的静态令牌验证，适用于开发和测试场景
   - 通过`Authorization: Bearer <token>`请求头传递
   - 支持全局Bearer Token和按航司Bearer Token

- **认证上下文（AuthContext）**：认证成功后生成AuthContext对象，携带airline、user、jwt_token、auth_method等信息，贯穿整个请求生命周期
- **速率限制**：基于slowapi库实现，默认每航司每分钟15次请求限制，防止API滥用
- **调用方传入的token**：优化任务执行时，调用方传入的JWT token用于与Live Server通信

### 9.2 数据安全

- 传输加密（HTTPS）
- 文件权限管理
- 航司数据隔离

### 9.3 系统安全

- 输入验证
- 错误处理
- 防止注入攻击

## 10. 故障处理

### 10.1 服务故障

- 服务自动重启
- 任务状态恢复

### 10.2 任务故障

- 任务重试机制
- 错误通知

### 10.3 网络故障

- 网络连接监控
- 重试机制

## 11. 版本管理

### 11.1 版本信息

- **版本号**：在 `version.py` 中定义（如 `VERSION = "1.0.0"`）
- **Git提交ID**：通过 `generate_git_properties.py` 脚本在编译时自动生成
- **提交作者**：通过 `generate_git_properties.py` 脚本在编译时自动生成
- **构建时间戳**：通过 `generate_git_properties.py` 脚本在编译时自动生成

### 11.2 版本生成流程

1. **编译时生成**：执行 `generate_git_properties.py` 脚本，生成 `git.properties` 文件
2. **运行时加载**：`version.py` 在启动时加载 `git.properties` 文件中的信息
3. **版本信息组合**：将版本号与Git提交信息组合成完整版本号（如 `1.0.0-9b4c525-2026-04-03 17:30:00`）

### 11.3 git.properties 文件结构

```properties
# Git 提交信息
git.commit.id=full_commit_hash
git.commit.id.abbrev=short_commit_hash
git.commit.author.name=commit_author
git.commit.time=commit_time
build.timestamp=build_timestamp
```

### 11.4 版本查询

- **API接口**：通过 `/api/system/info` 接口查询版本信息
- **版本信息包含**：服务名称、版本号、Git提交ID、提交作者、构建时间戳
- **PyInstaller支持**：支持从打包后的可执行文件中加载版本信息

### 11.5 版本管理工具

- **generate_git_properties.py**：生成包含Git提交信息的 `git.properties` 文件
- **version.py**：加载版本信息并提供版本查询功能

## 12. 分布式任务管理架构

### 12.1 架构设计

分布式任务管理架构采用Redis作为共享存储，实现多机部署时的任务状态同步。

#### 12.1.1 架构图

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Client    │────▶│  Load Balancer │◀────│   Client    │
└─────────────┘     └──────┬──────┘     └─────────────┘
                           │
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
      ┌─────────┐    ┌─────────┐    ┌─────────┐
      │ Server1 │    │ Server2 │    │ Server3 │
      │(Task运行)│    │(查询进度)│    │(停止任务)│
      └────┬────┘    └────┬────┘    └────┬────┘
           │               │               │
           └───────────────┼───────────────┘
                           ▼
                    ┌─────────────┐
                    │    Redis    │
                    │(共享状态存储) │
                    └─────────────┘
```

#### 12.1.2 核心组件

1. **Server实例**：多个优化引擎调度工具实例，部署在不同服务器上
2. **负载均衡器**：前端负载均衡，将请求分发到不同的Server实例
3. **Redis**：共享存储，存储任务状态和进度信息
4. **文件存储**：共享存储或文件同步，存储优化器和文件

### 12.2 工作流程

#### 12.2.1 任务创建和执行

1. **客户端请求**：客户端发送启动优化任务的请求，通过负载均衡器分发到某个Server实例
2. **任务创建**：Server实例创建任务，生成唯一任务ID，保存到本地内存和Redis
3. **任务执行**：Server实例执行优化任务，实时更新任务状态和进度到Redis
4. **状态同步**：其他Server实例通过Redis获取任务状态

#### 12.2.2 任务查询

1. **客户端请求**：客户端发送查询任务状态的请求，通过负载均衡器分发到某个Server实例
2. **任务查询**：Server实例先检查本地内存，如不存在则从Redis获取任务信息
3. **返回结果**：Server实例返回任务状态和进度信息

#### 12.2.3 任务停止

1. **客户端请求**：客户端发送停止任务的请求，通过负载均衡器分发到某个Server实例
2. **任务查找**：Server实例先检查本地内存，如不存在则从Redis获取任务信息
3. **任务停止**：
   - 如果任务在本地执行，直接停止任务
   - 如果任务在其他Server执行，通过Redis发布停止事件
4. **状态更新**：任务停止后，更新任务状态到Redis

### 12.3 技术实现

#### 12.3.1 Redis数据结构

- **任务数据**：`task:{task_id}`，存储任务详细信息，包括状态、进度、服务器ID等
- **任务过期**：设置TTL，自动清理已完成的任务数据

#### 12.3.2 事件机制

- **发布订阅**：使用Redis的发布订阅机制，实现任务事件的通知
- **事件类型**：
  - `task:{task_id}:progress`：进度更新事件
  - `task:{task_id}:status`：状态变更事件
  - `task:{task_id}:stop`：停止任务事件

#### 12.3.3 容错处理

- **服务器故障**：当执行任务的服务器故障时，其他服务器可以通过Redis获取任务状态
- **Redis故障**：当Redis故障时，系统退回到本地存储模式，保证基本功能
- **网络故障**：实现重试机制，确保任务状态同步

### 12.4 部署要求

#### 12.4.1 Redis部署

- **单节点Redis**：适用于小规模部署
- **Redis集群**：适用于大规模部署，提供高可用性
- **配置要求**：
  - 内存：根据任务数量和数据大小调整
  - 网络：确保所有Server实例能够访问Redis

#### 12.4.2 文件存储

- **NFS共享存储**：适用于小规模部署
- **分布式文件系统**：适用于大规模部署
- **同步要求**：确保所有Server实例能够访问相同的优化器和文件

## 13. 总结

优化引擎调度工具采用分层架构设计，模块化实现，支持按航司配置优化器，具有良好的扩展性和可维护性。系统支持多机部署，通过Redis实现任务状态的分布式同步，确保在多节点部署时的状态一致性。这种架构设计满足了企业内部多航司优化任务的管理需求，同时为系统的水平扩展提供了基础。
