# 认证方案设计评审与改进提案

> 日期: 2026-04-05
> 状态: 待确认

---

## 一、当前设计分析

### 1.1 现有认证流程

```
客户端请求
  ├─ Header: X-Airline: BR              (必须)
  ├─ Header: X-API-Key: your_key        (方式一: API Key)
  └─ Header: Authorization: Bearer xxx  (方式二: Bearer Token)
        │
        ▼
  verify_token() — src/api/auth.py
  ├─ auth.enabled=false → 直接放行
  ├─ 检查 X-Airline 是否存在
  ├─ 优先检查航司特定 API Key → 再检查全局 API Key
  └─ 再检查航司 Bearer Token → 再检查全局 Bearer Token
```

### 1.2 现有设计的优点

| 优点 | 说明 |
|------|------|
| 常量时间比较 | 使用 `hmac.compare_digest` 防止时序攻击 |
| 多层认证优先级 | 支持航司专属 key + 全局 key 回退 |
| 环境变量支持 | key 通过 `${ENV_VAR:default}` 从环境变量读取，不硬编码 |
| 实现简洁 | 代码量少，易于理解和维护 |

### 1.3 现有设计的安全问题

| 问题 | 严重程度 | 说明 |
|------|----------|------|
| API Key 静态，永不过期 | **高** | 一旦泄露无法自动失效，只能手动换 key 并重启服务 |
| 无请求频率限制 | **高** | 可被暴力猜测或滥用，无任何限流防护 |
| 所有接口共用同一个 key | **中** | 无法区分"只读查询"和"启动/停止任务"的权限 |
| 无审计日志关联 | **中** | 认证通过后只知道 airline，不知道具体是谁操作 |
| 无 HTTPS 强制 | **中** | API Key 在 HTTP 下明文传输，可被中间人截获 |
| key 无作用域限制 | **低** | 持有全局 key 可操作所有航司的所有接口 |

### 1.4 核心问题：没有登录系统，API Key 从哪来？

当前 API Key 的分发方式是**运维手动配置**：

1. 管理员在 `config.yaml` 中设置一个 key
2. 手动告诉客户端（前端/调度系统）这个 key
3. 客户端在每次请求中携带这个 key

这种方式有以下痛点：
- key 泄露了只能手动更换，影响所有客户端
- 无法知道是哪个用户/系统在使用这个 key
- 所有客户端共用一个 key，无法做权限区分
- key 的生命周期完全依赖人工管理

---

## 二、系统架构中的认证关系

从代码分析，整个系统中实际存在**两层认证**：

```
                                       ┌─────────────────────┐
                                       │     Live Server      │
                                       │  (已有用户账号体系)    │
                                       │  (已有 JWT 签发能力)   │
                                       └──────▲──────▲───────┘
                                              │      │
                                     input.gz │      │ output.gz
                                     (用JWT)  │      │ (用JWT)
                                              │      │
┌──────────────┐   X-API-Key ?   ┌────────────┴──────┴────────┐
│  客户端       │ ─────────────▶ │  Optimizer Server (本服务)   │
│ (前端/调度系统)│               │                              │
└──────────────┘               └───────────────────────────────┘
```

**关键发现：** 客户端调用 `/api/optimize/start` 时会传入 `url` 和 `token` 字段（Live Server 的 JWT），说明**客户端已经拥有 Live Server 签发的 JWT Token**。这意味着：

- 用户已经在 Live Server 完成了登录认证
- 用户手中已有一个合法的 JWT Token
- 这个 JWT 包含用户身份信息（userName 等）

---

## 三、改进方案：复用 Live Server JWT

### 3.1 核心思路

**不需要新建登录系统**。直接复用 Live Server 已签发的 JWT 来鉴权 Optimizer Server：

```
┌──────────────┐  ①登录      ┌─────────────────┐
│   用户/前端   │ ──────────▶ │   Live Server    │
│              │ ◀────────── │  (签发 JWT)       │
│              │   JWT       └─────────────────┘
│              │
│              │  ②带上同一个 JWT 调用 Optimizer Server
│              │  Authorization: Bearer eyJhbG...
│              │
│              │             ┌──────────────────────────────┐
│              │ ──────────▶ │   Optimizer Server            │
└──────────────┘             │  ③验证 JWT 签名 + 过期时间    │
                             │  ④从 JWT 提取 user / airline  │
                             │  ⑤用同一 JWT 调 Live Server   │
                             └──────────────────────────────┘
```

### 3.2 JWT Token 结构（参考 Live Server 已有格式）

从项目中已有的测试 Token 解析，Live Server 的 JWT payload 大致为：

```json
{
  "0": 1,
  "iss": "admin@pi-solution",
  "exp": 1775315589,
  "userName": "yuan.z"
}
```

Optimizer Server 只需要：
1. 用**与 Live Server 共享的密钥**验证签名
2. 检查 `exp`（过期时间）
3. 提取 `userName` 用于审计日志

### 3.3 认证优先级设计

```
请求进来
  │
  ├─ 有 Authorization: Bearer xxx ?
  │   │
  │   ├─ JWT 验证启用？
  │   │   ├─ 尝试 JWT 解码 (验证签名 + 过期时间)
  │   │   │   ├─ 成功 → 提取 userName → 通过 ✅
  │   │   │   └─ 签名/过期失败 → 继续尝试下一种方式
  │   │   └─ JWT 未启用 → 跳过
  │   │
  │   └─ Bearer Token 静态验证启用？
  │       ├─ 匹配航司 Token → 通过 ✅
  │       └─ 匹配全局 Token → 通过 ✅
  │
  ├─ 有 X-API-Key ?
  │   ├─ 匹配航司 API Key → 通过 ✅
  │   └─ 匹配全局 API Key → 通过 ✅
  │
  └─ 都没有 → 401 Unauthorized ❌
```

### 3.4 配置设计

```yaml
auth:
  enabled: true

  # === 方式1: JWT 验证 (推荐 — 面向有登录态的客户端) ===
  jwt:
    enabled: true
    # 与 Live Server 共享的 JWT 签名密钥
    # 必须与 Live Server 的 jwt.secret 保持一致
    secret: "${JWT_SECRET}"
    # 签名算法 (与 Live Server 一致)
    algorithm: "HS256"
    # 是否校验过期时间
    verify_exp: true

  # === 方式2: API Key (保留 — 面向脚本/定时任务/服务间调用) ===
  api_key:
    enabled: true
    key: "${ROIS_API_KEY:your_api_key_here}"

  # === 方式3: 静态 Bearer Token (保留向后兼容) ===
  bearer_token:
    enabled: false
    token: "${ROIS_BEARER_TOKEN:your_bearer_token_here}"

  # === 航司特定认证 (可选) ===
  airline_auth:
    BR:
      api_key: ""
      bearer_token: ""
    F8:
      api_key: ""
      bearer_token: ""
```

### 3.5 客户端调用方式对比

#### 方式 A：前端/有登录态的客户端（推荐 JWT）

```http
POST /api/optimize/start
Authorization: Bearer eyJhbGciOiJIUzI1NiJ9...  ← Live Server 签发的 JWT
Content-Type: application/json

{
  "airline": "BR",
  "type": "PO",
  "parameters": {"scenarioId": "3896"},
  "url": "http://live-server:8080",
  "user": "yuan.z"
}
```

- **token 不再需要在 body 中传递**（JWT 本身就是认证凭据，服务端可直接用它调 Live Server）
- `X-Airline` header 可从 JWT 或 body 中的 airline 字段获取，不再强制要求
- `user` 字段可从 JWT 的 `userName` 自动提取

#### 方式 B：脚本/定时任务/无登录态的调用（保留 API Key）

```http
POST /api/optimize/start
X-Airline: BR
X-API-Key: your_secret_key
Content-Type: application/json

{
  "airline": "BR",
  "type": "PO",
  "parameters": {"scenarioId": "3896"},
  "url": "http://live-server:8080",
  "token": "eyJhbG...",
  "user": "scheduler_bot"
}
```

- API Key 认证通过后，仍然需要在 body 中传 `token` 字段给 Live Server 使用
- 适合没有登录态的后台脚本

---

## 四、方案对比

| 维度 | 当前（静态 API Key） | 改进后（JWT + API Key 混合） |
|------|---------------------|----------------------------|
| 客户端如何拿到凭据 | 运维手动分发 key | JWT: 用户登录 Live Server 自动获得<br>API Key: 运维分发（保留给脚本） |
| 凭据过期 | 永不过期 | JWT: 自动过期（由 Live Server 控制）<br>API Key: 永不过期（保持简单） |
| 知道是谁在操作 | 不知道 | JWT: 从 `userName` 提取<br>API Key: 只知道是哪个 key |
| 泄露影响 | 永久有效，必须手动换 | JWT: 自动过期，窗口有限<br>API Key: 同当前 |
| 权限控制 | 无 | 可基于 JWT claims 扩展角色权限 |
| 对现有客户端的影响 | — | **零影响**，API Key 方式保持不变 |
| 实现复杂度 | — | 低（新增 PyJWT 依赖 + ~30 行代码） |

---

## 五、实现计划

### 5.1 代码改动清单

| 文件 | 改动内容 |
|------|----------|
| `requirements.txt` | 新增 `PyJWT>=2.8.0,<3.0.0` |
| `src/config/config.py` | 新增 `JWTConfig` 配置类 |
| `config.yaml` | 新增 `auth.jwt` 配置段 |
| `src/config/config.yaml.example` | 同步更新 |
| `src/api/auth.py` | 增加 JWT 解码验证逻辑（~30 行） |
| `src/api/routes.py` | `/optimize/start` 自动从 JWT 提取 token 给 Live Server |
| `tests/test_auth_and_errors.py` | 新增 JWT 认证测试用例 |

### 5.2 向后兼容保证

- API Key 方式**完全保留**，不做任何修改
- Bearer Token 静态验证**保留**
- JWT 作为**新增的优先验证方式**，不影响已有调用
- `X-Airline` header 在 API Key 模式下仍然需要

### 5.3 安全增强（可选，后续迭代）

| 增强项 | 说明 | 优先级 |
|--------|------|--------|
| 请求限流 | 集成 `slowapi`，限制每 IP/每 key 的请求频率 | 高 |
| JWT 角色权限 | 根据 JWT 中的 role 字段区分 admin/operator/viewer | 中 |
| HTTPS 强制 | 在反向代理层（Nginx）强制 HTTPS | 中 |
| API Key 轮换 | 支持同时存在两个有效 key，便于无缝轮换 | 低 |
| JWT 黑名单 | 支持主动吊销特定 JWT（需要 Redis） | 低 |

---

## 六、待确认事项

请确认以下问题后开始实施：

1. **Live Server 的 JWT 签名算法和密钥**：
   - 签名算法是 `HS256`（HMAC-SHA256）还是 `RS256`（RSA）？
   - 如果是 HS256：Optimizer Server 需要配置相同的 `secret`
   - 如果是 RS256：Optimizer Server 只需要 Live Server 的公钥

2. **JWT Payload 结构**：
   - 从已有测试 Token 看到的字段有：`iss`, `exp`, `userName`
   - 是否还有 `airline` 或 `role` 等字段？
   - 如果 JWT 中没有 airline，客户端仍需通过 `X-Airline` header 或 body 传入

3. **是否需要保留 body 中的 `token` 字段**：
   - JWT 模式下，Header 中的 JWT 可以直接用来调用 Live Server
   - 是否仍需要支持客户端在 body 中传一个不同的 token 给 Live Server？
   - 场景：用户用自己的 JWT 鉴权，但指定另一个服务账号的 token 调 Live Server

4. **API Key 是否仍然需要**：
   - 是否有脚本/定时任务等无登录态的调用场景？
   - 如果有，API Key 保留；如果没有，可以简化为仅 JWT

5. **请求限流需求**：
   - 是否需要限流？如果需要，每分钟允许多少次请求？
   - 限流维度：按 IP？按 airline？按 user？

---

> **确认后我将开始实施。所有改动都向后兼容，不影响现有 API Key 调用方式。**
