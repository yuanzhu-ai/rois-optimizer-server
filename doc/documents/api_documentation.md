# 优化引擎调度工具 - API接口文档

## 1. 接口概述

优化引擎调度工具提供RESTful API接口，用于管理和调度优化任务。系统支持按航司配置不同的优化器版本，采用三层认证体系（JWT > API Key > Bearer Token），并支持基于航司的速率限制。

## 2. 认证方式

系统支持三种认证方式，按优先级从高到低依次为：JWT > API Key > Bearer Token（静态）。

### 2.1 JWT认证（推荐，最高优先级）

- **认证类型**：JWT (HS256) 认证
- **Token来源**：使用Live Server签发的JWT Token
- **传递方式**：通过请求头 `Authorization: Bearer <jwt_token>` 传递
- **验证方式**：使用与Live Server共享的密钥（`auth.jwt.secret`）验证签名
- **用户提取**：从JWT payload中提取 `userName` 字段，作为当前操作用户
- **Live Server通信**：JWT模式下，请求头中的JWT Token会自动传递给Live Server，请求body中的 `token` 字段为可选
- **返回对象**：验证成功后返回 `AuthContext`，包含 airline、user、jwt_token、auth_method

### 2.2 API Key认证（次优先级）

- **认证类型**：API Key认证
- **传递方式**：通过请求头 `X-API-Key` 传递API Key
- **适用场景**：Live Server对优化引擎的服务间调用（无登录状态）
- **说明**：API Key模式下没有用户登录状态，适用于系统间自动化调用
- **返回对象**：验证成功后返回 `AuthContext`，包含 airline、auth_method

### 2.3 Bearer Token认证（静态，最低优先级）

- **认证类型**：Bearer Token（静态配置）
- **传递方式**：通过请求头 `Authorization: Bearer <token>` 传递
- **验证方式**：与config.yaml中配置的静态token比对
- **说明**：当Authorization头中的Token不是合法JWT时，回退为静态Bearer Token验证
- **返回对象**：验证成功后返回 `AuthContext`，包含 airline、auth_method

### 2.4 认证上下文（AuthContext）

认证成功后，`verify_token` 函数返回 `AuthContext` 对象，包含以下字段：

| 字段 | 说明 |
| --- | --- |
| `airline` | 航司二字码，来自 `X-Airline` 请求头 |
| `user` | 用户标识，JWT模式从payload提取userName，其他模式为None |
| `jwt_token` | JWT Token字符串，仅JWT模式下有值 |
| `auth_method` | 认证方式：`jwt`、`api_key` 或 `bearer_token` |

### 2.5 速率限制

- **限制规则**：每个航司（通过 `X-Airline` 请求头识别）每分钟最多15次请求
- **超限响应**：返回HTTP状态码 `429 Too Many Requests`
- **配置方式**：在config.yaml中通过 `auth.rate_limit` 配置

### 2.6 Live Server认证

- **JWT模式**：请求头中的JWT Token自动传递给Live Server，body中的 `token` 字段可选
- **非JWT模式**：由客户端在请求body中传入 `token` 字段，用于调用Live Server
- **说明**：Live Server的认证与优化引擎Server的认证是独立的

## 3. 接口列表

### 3.1 优化任务管理接口

#### 3.1.1 启动优化任务

- **接口**：`POST /api/optimize/start`
- **描述**：启动一个新的优化任务
- **请求头**：
  - `X-Airline`：航司二字码（必填），如F8、BR
  - `Authorization`：`Bearer <jwt_token>` JWT认证（推荐），或 `Bearer <static_token>` 静态Token认证
  - `X-API-Key`：API Key认证（用于服务间调用）
- **参数**：
  - `airline`：航司二字码（必填），如F8、BR
  - `url`：Live Server基础URL（必填），如 http://localhost
  - `token`：Live Server认证Token（JWT模式下可选，非JWT模式必填），用于调用Live Server
  - `user`：用户ID（必填，JWT模式下从token自动提取userName）
  - `type`：优化器类型（必填），如PO、RO、TO、Rule
  - `parameters`：优化参数（可选），JSON对象
- **返回**：
  ```json
  {
    "task_id": "task_123",
    "status": "started"
  }
  ```
- **示例请求（JWT认证，推荐）**：
  ```bash
  curl -X POST "http://localhost:8000/api/optimize/start" \
    -H "X-Airline: F8" \
    -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..." \
    -H "Content-Type: application/json" \
    -d '{
      "airline": "F8",
      "url": "http://localhost",
      "user": "0001",
      "type": "PO",
      "parameters": {"scenarioId": "123"}
    }'
  ```
  > 注意：JWT模式下 `token` 字段可省略，系统自动使用请求头中的JWT Token与Live Server通信。
- **示例请求（API Key认证）**：
  ```bash
  curl -X POST "http://localhost:8000/api/optimize/start" \
    -H "X-Airline: F8" \
    -H "X-API-Key: your_api_key_here" \
    -H "Content-Type: application/json" \
    -d '{
      "airline": "F8",
      "url": "http://localhost",
      "token": "123456",
      "user": "0001",
      "type": "PO",
      "parameters": {"scenarioId": "123"}
    }'
  ```
- **工作目录命名规则**：
  - **PO/RO/TO**: `{type}_{scenarioId}_{timestamp}_{taskId}`
    - 例如: `PO_3896_20260404_003315_2075d6f6`
  - **Rule**: `{category}_{timestamp}_{taskId}`
    - 例如: `manday_byCrew_20260404_003322_cbd11bbe`
- **Live Server URL构建规则**：
  - 最终URL = `{url}{config中的input路径}`
  - 例如: `http://localhost/api/orengine/po/comptxt`
- **Live Server请求数据格式**：
  - **PO/RO/TO类型**：发送纯整数 `scenarioId`
    - 例如: 直接发送 `3896`
  - **Rule类型**：发送JSON对象，包含 `scenarioId` 等参数
    - 例如: `{"scenarioId": 3896, "category": "manday_byCrew", ...}`

#### 3.1.2 停止优化任务

- **接口**：`POST /api/optimize/stop/{task_id}`
- **描述**：停止指定的优化任务
- **请求头**：
  - `X-Airline`：航司二字码（必填），如F8、BR
- **参数**：
  - `task_id`：任务ID
- **返回**：
  ```json
  {
    "task_id": "task_123",
    "status": "stopped"
  }
  ```
- **示例请求**：
  ```bash
  curl -X POST "http://localhost:8000/api/optimize/stop/task_123" \
    -H "X-Airline: F8" \
    -H "Authorization: Bearer your_secret_token"
  ```

#### 3.1.3 查询优化任务状态

- **接口**：`GET /api/optimize/status/{task_id}`
- **描述**：查询指定优化任务的状态
- **请求头**：
  - `X-Airline`：航司二字码（必填），如F8、BR
- **参数**：
  - `task_id`：任务ID
- **返回**：
  ```json
  {
    "task_id": "task_123",
    "status": "running",
    "airline": "F8",
    "optimizer_type": "PO",
    "error_message": null
  }
  ```
- **示例请求**：
  ```bash
  curl -X GET "http://localhost:8000/api/optimize/status/task_123" \
    -H "X-Airline: F8" \
    -H "Authorization: Bearer your_secret_token"
  ```

#### 3.1.4 查询优化任务进度

- **接口**：`GET /api/optimize/progress/{task_id}`
- **描述**：查询指定优化任务的进度
- **请求头**：
  - `X-Airline`：航司二字码（必填），如F8、BR
- **参数**：
  - `task_id`：任务ID
- **返回**：
  ```json
  {
    "task_id": "task_123",
    "progress": 50,
    "status": "running",
    "airline": "F8"
  }
  ```
- **示例请求**：
  ```bash
  curl -X GET "http://localhost:8000/api/optimize/progress/task_123" \
    -H "X-Airline: F8" \
    -H "Authorization: Bearer your_secret_token"
  ```

### 3.2 系统管理接口

#### 3.2.1 获取系统信息

- **接口**：`GET /api/system/info`
- **描述**：获取系统信息，包括版本信息
- **请求头**：
  - `X-Airline`：航司二字码（必填），如F8、BR
- **返回**：
  ```json
  {
    "service": "优化引擎调度工具",
    "version": "1.0.0-9b4c525-2026-04-03 17:30:00",
    "git_commit_id": "9b4c525",
    "commit_author": "yuan.zhu",
    "build_timestamp": "2026-04-03 17:30:00",
    "status": "running"
  }
  ```
- **示例请求**：
  ```bash
  curl -X GET "http://localhost:8000/api/system/info" \
    -H "X-Airline: F8" \
    -H "Authorization: Bearer your_secret_token"
  ```

#### 3.2.2 获取优化器列表

- **接口**：`GET /api/optimizers`
- **描述**：获取指定航司的所有可用优化器类型
- **请求头**：
  - `X-Airline`：航司二字码（必填），如F8、BR
- **返回**：
  ```json
  {
    "optimizers": ["PO", "RO", "TO", "Rule"]
  }
  ```
- **示例请求**：
  ```bash
  curl -X GET "http://localhost:8000/api/optimizers" \
    -H "X-Airline: F8" \
    -H "Authorization: Bearer your_secret_token"
  ```

#### 3.2.3 获取运行中任务

- **接口**：`GET /api/tasks/running`
- **描述**：获取指定航司的运行中任务
- **请求头**：
  - `X-Airline`：航司二字码（必填），如F8、BR
- **返回**：
  ```json
  {
    "tasks": [
      {
        "task_id": "task_123",
        "airline": "F8",
        "optimizer_type": "PO",
        "status": "running",
        "progress": 50,
        "start_time": 1620000000
      }
    ]
  }
  ```
- **示例请求**：
  ```bash
  # 获取指定航司的运行中任务
  curl -X GET "http://localhost:8000/api/tasks/running" \
    -H "X-Airline: F8" \
    -H "Authorization: Bearer your_secret_token"
  ```

#### 3.2.4 获取所有任务

- **接口**：`GET /api/tasks/all`
- **描述**：获取指定航司的所有任务
- **请求头**：
  - `X-Airline`：航司二字码（必填），如F8、BR
- **返回**：
  ```json
  {
    "tasks": [
      {
        "task_id": "task_123",
        "airline": "F8",
        "optimizer_type": "PO",
        "status": "completed",
        "progress": 100,
        "start_time": 1620000000,
        "end_time": 1620000100,
        "error_message": null
      }
    ]
  }
  ```
- **示例请求**：
  ```bash
  # 获取指定航司的所有任务
  curl -X GET "http://localhost:8000/api/tasks/all" \
    -H "X-Airline: F8" \
    -H "Authorization: Bearer your_secret_token"
  ```

## 4. 优化器类型说明

系统支持以下优化器类型，每种类型有不同的参数：

### 4.1 PO（Pairing Optimizer）

- **描述**：配对优化器
- **Live Server请求格式**：纯整数 `scenarioId`
- **示例参数**：
  ```json
  {
    "scenarioId": "123"
  }
  ```

### 4.2 RO（Roster Optimizer）

- **描述**：排班优化器
- **Live Server请求格式**：纯整数 `scenarioId`
- **示例参数**：
  ```json
  {
    "scenarioId": "345"
  }
  ```

### 4.3 TO（Training Optimizer）

- **描述**：培训优化器
- **Live Server请求格式**：纯整数 `scenarioId`
- **示例参数**：
  ```json
  {
    "scenarioId": "789"
  }
  ```

### 4.4 Rule（规则检查）

- **描述**：规则检查优化器
- **Live Server请求格式**：JSON对象
- **支持多种规则类型**：
  - **change_flight**：换班规则
    ```json
    {
      "category": "change_flight",
      "scenarioId": "0",
      "airline": "F8",
      "fltId": "1,2,3,4,5,6,7",
      "division": "C"
    }
    ```
  - **manday**：人日规则
    ```json
    {
      "category": "manday",
      "scenarioId": "0",
      "startDt": "2024-01-01",
      "endDt": "2024-08-31",
      "division": "C"
    }
    ```
  - **manday_byCrew**：按机组人员的人日规则
    ```json
    {
      "category": "manday_byCrew",
      "scenarioId": "0",
      "crewIds": "I73313,H47887,I73647,E53500",
      "startDt": "2024-01-01",
      "endDt": "2024-08-31",
      "division": "P"
    }
    ```

## 5. 航司配置

### 5.1 支持的航司

系统支持多个航司，每个航司可以配置不同的优化器版本：

- **F8**：示例航司1
- **BR**：示例航司2
- 可以通过配置文件添加更多航司

### 5.2 航司目录结构

每个航司有独立的目录结构：

```
{airline}/
├── optimizers/    # 优化器可执行文件
├── finished/      # 完成的优化结果
└── archive/       # 归档文件
```

### 5.3 配置文件示例

```yaml
# 服务器配置
server:
  host: 0.0.0.0
  port: 8000
  debug: true

# 认证配置
auth:
  enabled: true  # 是否启用认证
  # JWT认证（最高优先级，推荐）
  jwt:
    enabled: true  # 是否启用JWT认证
    secret: your_shared_jwt_secret  # 与Live Server共享的JWT密钥
    algorithm: HS256  # JWT签名算法
  # API Key认证（次优先级，用于服务间调用）
  api_key:
    enabled: true  # 是否启用API Key认证
    key: your_api_key_here  # 全局API Key值
  # Bearer Token认证（静态，最低优先级）
  bearer_token:
    enabled: true  # 是否启用Bearer Token认证
    token: your_bearer_token_here  # 全局Bearer Token值
  # 速率限制
  rate_limit:
    enabled: true  # 是否启用速率限制
    requests_per_minute: 15  # 每航司每分钟最大请求数

# 文件路径配置
paths:
  working_dir: ./workspace  # 工作目录
  finished_dir: ./finished  # 完成文件目录
  archive_dir: ./archive  # 归档目录
  temp_dir: ./temp  # 临时目录

# 航司配置
airlines:
  F8:
    optimizers:
      PO:
        name: Pairing Optimizer  # 优化器名称
        linux:
          path: ./F8/po.sh  # Linux平台执行路径
        windows:
          path: ./F8/po.bat  # Windows平台执行路径
      RO:
        name: Roster Optimizer  # 优化器名称
        linux:
          path: ./F8/ro.sh  # Linux平台执行路径
        windows:
          path: ./F8/ro.bat  # Windows平台执行路径
      TO:
        name: Training Optimizer  # 优化器名称
        linux:
          path: ./F8/to.sh  # Linux平台执行路径
        windows:
          path: ./F8/to.bat  # Windows平台执行路径
      Rule:
        name: Rule Checker  # 优化器名称
        linux:
          path: ./F8/rule.sh  # Linux平台执行路径
        windows:
          path: ./F8/rule.bat  # Windows平台执行路径
  BR:
    optimizers:
      PO:
        name: Pairing Optimizer  # 优化器名称
        linux:
          path: ./BR/po.sh  # Linux平台执行路径
        windows:
          path: ./BR/po.bat  # Windows平台执行路径
      RO:
        name: Roster Optimizer  # 优化器名称
        linux:
          path: ./BR/ro.sh  # Linux平台执行路径
        windows:
          path: ./BR/ro.bat  # Windows平台执行路径
      TO:
        name: Training Optimizer  # 优化器名称
        linux:
          path: ./BR/to.sh  # Linux平台执行路径
        windows:
          path: ./BR/to.bat  # Windows平台执行路径
      Rule:
        name: Rule Checker  # 优化器名称
        linux:
          path: ./BR/rule.sh  # Linux平台执行路径
        windows:
          path: ./BR/rule.bat  # Windows平台执行路径

# 文件管理配置
file_management:
  archive_days: 1  # 归档天数
  cleanup_days: 30  # 清理天数

# 任务配置
tasks:
  max_concurrent: 10  # 最大并发任务数
  timeout: 3600  # 任务超时时间（秒）

# HTTP客户端配置
http_client:
  # Live Server请求超时时间（秒）
  # 注：input.gz生成可能需要1-3分钟，建议设置20分钟（1200秒）
  timeout: 1200
```

### 5.4 HTTP客户端配置

系统支持配置HTTP客户端的超时时间，用于控制与Live Server通信的请求超时。

#### 5.4.1 配置说明

- **timeout**: Live Server请求超时时间（秒）
  - 默认值：1200秒（20分钟）
  - 建议值：1200秒（20分钟），因为input.gz生成可能需要1-3分钟，复杂的优化任务可能需要更长时间
  - 可根据实际网络环境和Live Server响应速度调整

#### 5.4.2 配置示例

```yaml
http_client:
  timeout: 600  # 10分钟
```

### 5.5 目录检查

系统在启动时会自动检查以下内容，确保配置正确：

1. **航司目录**：检查每个配置的航司目录是否存在（如 `./F8`、`./BR`）
2. **优化器路径**：检查每个优化器的 Linux 和 Windows 路径是否存在
3. **优化器文件**：检查每个优化器的路径是否是一个文件
4. **优化器目录**：检查航司的优化器目录是否为空，为空时给出警告

**错误提示示例：**
- 如果航司目录不存在：`"航司目录 ./F8 不存在，请先创建该目录"`
- 如果优化器 Linux 路径不存在：`"优化器 PO 的Linux路径 ./F8/po.sh 不存在，请先配置好对应的优化器"`
- 如果优化器 Linux 路径不是文件：`"优化器 PO 的Linux路径 ./F8/po.sh 不是一个文件，请先配置好对应的优化器"`
- 如果优化器 Windows 路径不存在：`"优化器 PO 的Windows路径 ./F8/po.bat 不存在，请先配置好对应的优化器"`
- 如果优化器 Windows 路径不是文件：`"优化器 PO 的Windows路径 ./F8/po.bat 不是一个文件，请先配置好对应的优化器"`
- 如果优化器目录为空：`"警告：航司 F8 的优化器目录 ./F8/optimizers 为空，请确保优化器文件存在"`

### 5.6 安全认证配置

系统采用三层认证体系（JWT > API Key > Bearer Token），并支持基于航司的速率限制。

#### 5.6.1 配置文件示例

```yaml
# 认证配置
auth:
  enabled: true  # 是否启用认证
  # JWT认证（最高优先级）
  jwt:
    enabled: true
    secret: your_shared_jwt_secret  # 与Live Server共享的JWT密钥
    algorithm: HS256
  # API Key认证（次优先级）
  api_key:
    enabled: true
    key: your_api_key_here
  # Bearer Token认证（最低优先级）
  bearer_token:
    enabled: true
    token: your_bearer_token_here
  # 速率限制
  rate_limit:
    enabled: true
    requests_per_minute: 15  # 每航司每分钟最大请求数
```

#### 5.6.2 认证流程

1. **航司二字码**：通过请求头 `X-Airline` 传递航司二字码（必填）
2. **速率限制检查**：检查该航司是否超过每分钟15次请求限制，超限返回 `429`
3. **JWT认证（最高优先级）**：检查 `Authorization: Bearer <token>` 头，尝试用共享密钥验证JWT签名（HS256），成功则提取 `userName`，JWT Token自动传递给Live Server
4. **API Key认证（次优先级）**：检查 `X-API-Key` 头，与配置的API Key比对
5. **Bearer Token认证（最低优先级）**：JWT验证失败时，将Authorization头中的Token与配置的静态Token比对
6. **返回AuthContext**：认证成功后返回包含 airline、user、jwt_token、auth_method 的上下文对象

#### 5.6.3 客户端请求示例

**使用JWT认证（推荐）：**

```python
import requests

# JWT Token从Live Server登录获取
jwt_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

headers = {
    "X-Airline": "F8",  # 航司二字码
    "Authorization": f"Bearer {jwt_token}"  # Live Server签发的JWT
}

# JWT模式下token字段可省略，系统自动使用请求头中的JWT
response = requests.post(
    "http://localhost:8000/api/optimize/start",
    json={
        "airline": "F8",
        "url": "http://localhost",
        "user": "0001",
        "type": "PO",
        "parameters": {"scenarioId": "123"}
    },
    headers=headers
)
```

**使用API Key认证（服务间调用）：**

```python
import requests

headers = {
    "X-Airline": "F8",  # 航司二字码
    "X-API-Key": "your_api_key_here"  # API Key
}

response = requests.post(
    "http://localhost:8000/api/optimize/start",
    json={
        "airline": "F8",
        "url": "http://localhost",
        "token": "live_server_token",  # 非JWT模式需要提供token
        "user": "0001",
        "type": "PO",
        "parameters": {"scenarioId": "123"}
    },
    headers=headers
)
```

**使用Bearer Token认证（静态）：**

```python
import requests

headers = {
    "X-Airline": "F8",  # 航司二字码
    "Authorization": "Bearer your_static_bearer_token"  # 静态Token
}

response = requests.post(
    "http://localhost:8000/api/optimize/start",
    json={
        "airline": "F8",
        "url": "http://localhost",
        "token": "live_server_token",  # 非JWT模式需要提供token
        "user": "0001",
        "type": "PO",
        "parameters": {"scenarioId": "123"}
    },
    headers=headers
)
```

## 6. 状态码

| 状态码 | 描述 |
| --- | --- |
| 200 | 成功 |
| 400 | 请求参数错误 |
| 401 | 认证失败（JWT无效、API Key错误、Bearer Token不匹配） |
| 404 | 资源不存在 |
| 429 | 请求频率超限（每航司每分钟15次） |
| 500 | 服务器内部错误 |

## 7. 错误处理

当请求失败时，API会返回错误信息：

```json
{
  "detail": "错误信息"
}
```

## 8. 示例请求

### 8.1 启动PO优化任务

```bash
curl -X POST "http://localhost:8000/api/optimize/start" \
  -H "X-Airline: F8" \
  -H "Authorization: Bearer your_secret_token" \
  -H "Content-Type: application/json" \
  -d '{
    "airline": "F8",
    "url": "http://localhost",
    "token": "123456",
    "user": "0001",
    "type": "PO",
    "parameters": {"scenarioId": "123"}
  }'
```

### 8.2 启动TO优化任务

```bash
curl -X POST "http://localhost:8000/api/optimize/start" \
  -H "X-Airline: F8" \
  -H "Authorization: Bearer your_secret_token" \
  -H "Content-Type: application/json" \
  -d '{
    "airline": "F8",
    "url": "http://localhost",
    "token": "123456",
    "user": "0001",
    "type": "TO",
    "parameters": {"scenarioId": "789"}
  }'
```

### 8.3 启动RO优化任务

```bash
curl -X POST "http://localhost:8000/api/optimize/start" \
  -H "X-Airline: BR" \
  -H "Authorization: Bearer your_secret_token" \
  -H "Content-Type: application/json" \
  -d '{
    "airline": "BR",
    "url": "http://localhost:8080",
    "token": "456788",
    "user": "AAA1",
    "type": "RO",
    "parameters": {"scenarioId": "345"}
  }'
```

### 8.4 启动Rule优化任务（change_flight）

```bash
curl -X POST "http://localhost:8000/api/optimize/start" \
  -H "X-Airline: F8" \
  -H "Authorization: Bearer your_secret_token" \
  -H "Content-Type: application/json" \
  -d '{
    "airline": "F8",
    "url": "http://localhost",
    "token": "123456",
    "user": "0001",
    "type": "Rule",
    "parameters": {
      "category": "change_flight",
      "scenarioId": "0",
      "airline": "F8",
      "fltId": "1,2,3,4,5,6,7",
      "division": "C"
    }
  }'
```

### 8.5 启动Rule优化任务（manday）

```bash
curl -X POST "http://localhost:8000/api/optimize/start" \
  -H "X-Airline: F8" \
  -H "Authorization: Bearer your_secret_token" \
  -H "Content-Type: application/json" \
  -d '{
    "airline": "F8",
    "url": "http://localhost",
    "token": "123456",
    "user": "0001",
    "type": "Rule",
    "parameters": {
      "category": "manday",
      "scenarioId": "0",
      "startDt": "2024-01-01",
      "endDt": "2024-08-31",
      "division": "C"
    }
  }'
```

### 8.6 启动Rule优化任务（manday_byCrew）

```bash
curl -X POST "http://localhost:8000/api/optimize/start" \
  -H "X-Airline: F8" \
  -H "Authorization: Bearer your_secret_token" \
  -H "Content-Type: application/json" \
  -d '{
    "airline": "F8",
    "url": "http://localhost",
    "token": "123456",
    "user": "0001",
    "type": "Rule",
    "parameters": {
      "category": "manday_byCrew",
      "scenarioId": "0",
      "crewIds": "I73313,H47887,I73647,E53500",
      "startDt": "2024-01-01",
      "endDt": "2024-08-31",
      "division": "P"
    }
  }'
```

### 8.7 查询任务状态

```bash
curl -X GET "http://localhost:8000/api/optimize/status/task_123" \
  -H "X-Airline: F8" \
  -H "Authorization: Bearer your_secret_token"
```

### 8.8 获取F8航司的优化器列表

```bash
curl -X GET "http://localhost:8000/api/optimizers" \
  -H "X-Airline: F8" \
  -H "Authorization: Bearer your_secret_token"
```

### 8.9 获取F8航司的所有任务

```bash
curl -X GET "http://localhost:8000/api/tasks/all" \
  -H "X-Airline: F8" \
  -H "Authorization: Bearer your_secret_token"
```

## 9. 接口使用注意事项

1. **认证**：推荐使用JWT认证（与Live Server共享密钥），系统支持三层认证体系：JWT > API Key > Bearer Token
2. **航司二字码**：必须通过请求头 `X-Airline` 传递航司二字码，用于认证校验、航司隔离和速率限制
3. **速率限制**：每个航司每分钟最多15次请求，超限返回429状态码
4. **优化器类型**：支持的优化器类型包括PO、RO、TO、Rule
5. **任务状态**：任务状态包括pending、running、completed、failed、stopped
6. **并发限制**：系统有最大并发任务数限制，请合理安排任务
7. **错误处理**：请妥善处理API返回的错误信息
8. **航司隔离**：不同航司的任务和优化器是相互隔离的
9. **Live Server认证**：JWT模式下Token自动从请求头传递给Live Server；非JWT模式需要在body中传入token字段

## 10. 接口版本管理

- **当前版本**：v1.0.0
- **版本控制**：通过URL路径控制，如`/api/v1/optimize/start`
- **兼容性**：后续版本会保持向后兼容

## 11. 性能建议

1. **批量操作**：对于多个任务的操作，建议使用批量接口
2. **缓存**：对于频繁查询的接口，建议使用缓存
3. **限流**：请合理控制请求频率，避免过载
4. **异步处理**：对于长时间运行的任务，建议使用异步接口
5. **航司过滤**：查询任务时，建议传入airline参数进行过滤，提高查询效率

## 12. 测试状态

### 12.1 自动化测试

全部 **105项测试** 已通过（92项原有测试 + 12项JWT认证测试 + 1项新增认证测试）。

| 测试类别 | 数量 | 状态 |
|----------|------|------|
| 原有功能测试 | 92 | ✅ 全部通过 |
| JWT认证测试 | 12 | ✅ 全部通过 |
| 新增认证测试 | 1 | ✅ 全部通过 |
| **合计** | **105** | **✅ 全部通过** |

### 12.2 功能测试进度

| 优化器 | 类型 | Input测试 | Output测试 | 状态说明 |
|--------|------|-----------|------------|----------|
| **PO** | - | ✅ 通过 | ⏳ 待测试 | 已验证获取input.gz（705KB） |
| **RO** | - | ✅ 通过 | ⏳ 待测试 | 已验证获取input.gz（10.6MB） |
| **Rule** | change_flight | ✅ 通过 | ⏳ 待测试 | 已验证获取input.gz（1.1MB） |
| | manday | ⏳ 测试中 | ⏳ 待测试 | - |
| | manday_byCrew | ⏳ 测试中 | ⏳ 待测试 | - |

**说明**：
- ✅ 通过：已完成功能测试并验证成功
- ⏳ 待测试：功能已实现，待后续测试验证
- ❌ 失败：测试未通过，需要修复

### 12.3 已验证功能

1. **工作目录命名规则**
   - PO/RO/TO: `{type}_{scenarioId}_{timestamp}_{taskId}`
   - Rule: `{category}_{timestamp}_{taskId}`

2. **Live Server URL构建**
   - 使用调用方传入的url参数
   - 格式: `{url}{config中的input路径}`

3. **请求数据格式**
   - PO/RO/TO: 纯整数 `scenarioId`
   - Rule: JSON对象（包含category等参数）

4. **认证逻辑（三层体系）**
   - JWT认证（最高优先级）：使用Live Server共享密钥验证，自动提取userName，JWT自动传递给Live Server
   - API Key认证（次优先级）：用于Live Server服务间调用，无登录状态
   - Bearer Token认证（最低优先级）：静态Token比对
   - 返回AuthContext对象（含airline、user、jwt_token、auth_method）

5. **速率限制**
   - 每航司每分钟15次请求限制
   - 超限返回429状态码

6. **超时配置**
   - 默认20分钟（1200秒）
   - 可在config.yaml中调整

## 13. 总结

优化引擎调度工具的API接口设计简洁明了，支持按航司配置优化器，提供了完整的优化任务管理功能。通过这些接口，客户端可以方便地创建、启动、停止和监控优化任务，实现对优化过程的全程管理。
