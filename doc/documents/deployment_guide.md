# 优化引擎调度工具 - 部署指南

## 1. 环境准备

### 1.1 系统要求

- **操作系统**：Windows 10+ 或 Linux
- **Python**：Python 3.8 或更高版本
- **网络**：支持HTTP/HTTPS协议

### 1.2 依赖包

优化引擎调度工具需要以下依赖包：

- fastapi
- uvicorn
- pydantic
- pydantic-settings
- pyyaml
- requests
- python-multipart
- pytest（可选，用于测试）

## 2. 安装步骤

### 2.1 克隆代码库

```bash
# 克隆代码库
git clone <repository_url>
cd optimize-server
```

### 2.2 安装依赖包

```bash
# 安装依赖包
pip install -r requirements.txt
```

### 2.3 配置文件

1. **复制配置文件示例**：

```bash
# 复制配置文件示例
cp src/config/config.yaml.example src/config/config.yaml
```

2. **编辑配置文件**：根据实际情况修改 `src/config/config.yaml` 文件中的配置项。

主要配置项包括：

- **server**：服务器配置（主机、端口、调试模式）
- **auth**：认证配置（是否启用、token）
- **paths**：文件路径配置（工作目录、Finished目录、archive目录、临时目录）
- **optimizers**：优化器配置（不同平台的执行路径和参数）
- **file_management**：文件管理配置（归档天数、清理天数）
- **tasks**：任务配置（最大并发数、超时时间）

## 3. 运行服务

### 3.1 源码部署

#### 3.1.1 Windows平台

在Windows平台上，使用 `start.bat` 脚本启动服务：

```cmd
# 启动服务
start.bat
```

#### 3.1.2 Linux平台

在Linux平台上，使用 `start.sh` 脚本启动服务：

```bash
# 给脚本添加执行权限
chmod +x start.sh

# 启动服务
./start.sh
```

#### 3.1.3 手动启动

也可以手动启动服务：

```bash
# 启动服务
uvicorn main:app --host 0.0.0.0 --port 8000
```

### 3.2 可执行文件部署（推荐）

#### 3.2.1 Windows 可执行文件

1. **下载可执行文件**
   - 从构建服务器或发布渠道获取 `optimize_server.exe` 文件

2. **运行可执行文件**
   - 直接双击 `optimize_server.exe` 文件启动服务
   - 或在命令提示符中运行：`optimize_server.exe`

#### 3.2.2 Linux 可执行文件

1. **下载可执行文件**
   - 从构建服务器或发布渠道获取 `optimize_server` 文件

2. **设置执行权限**
   - 打开终端
   - 进入可执行文件目录
   - 设置执行权限：`chmod +x optimize_server`

3. **运行可执行文件**
   - 直接运行：`./optimize_server`

## 4. 编译打包

### 4.1 Windows 编译

1. **安装依赖**
   - 打开命令提示符（CMD）
   - 进入项目目录：`cd optimize-server`
   - 安装依赖：`pip install -r requirements.txt`
   - 安装 PyInstaller：`pip install pyinstaller`

2. **生成版本信息**
   - 运行：`python generate_git_properties.py`

3. **打包项目**
   - 运行：`pyinstaller optimize_server.spec`

4. **获取可执行文件**
   - 可执行文件位于 `dist` 目录中：`dist/optimize_server.exe`

### 4.2 Linux 编译

1. **安装依赖**
   - 打开终端
   - 进入项目目录：`cd optimize-server`
   - 安装依赖：`pip3 install -r requirements.txt`
   - 安装 PyInstaller：`pip3 install pyinstaller`

2. **生成版本信息**
   - 运行：`python3 generate_git_properties.py`

3. **打包项目**
   - 运行：`pyinstaller optimize_server.spec`

4. **获取可执行文件**
   - 可执行文件位于 `dist` 目录中：`dist/optimize_server`

### 4.3 使用 Docker 跨平台编译

如果没有 Linux 环境，可以使用 Docker 来模拟 Linux 环境进行打包：

```bash
# 拉取 Python 镜像
docker pull python:3.10-slim

# 运行 Docker 容器并执行打包命令
docker run --rm -v $(pwd):/app -w /app python:3.10-slim bash -c "
    pip install pyinstaller
    pip install -r requirements.txt
    python generate_git_properties.py
    pyinstaller optimize_server.spec
"
```

## 5. 验证服务

### 5.1 检查服务状态

服务启动后，可以通过以下方式检查服务状态：

```bash
# 检查服务状态
curl -X GET "http://localhost:8000/health"
```

预期响应：

```json
{
  "status": "healthy"
}
```

### 5.2 测试API接口

测试获取系统信息的API接口：

```bash
# 测试API接口
curl -X GET "http://localhost:8000/api/system/info" -H "Authorization: Bearer your_secret_token"
```

预期响应：

```json
{
  "service": "优化引擎调度工具",
  "version": "1.0.0",
  "status": "running"
}
```

## 6. 多机部署

### 6.1 配置共享存储

如果需要在多台服务器上部署优化引擎调度工具，建议使用共享存储来存储文件：

- **NFS**：Network File System（Linux）
- **SMB**：Server Message Block（Windows）
- **云存储**：如AWS S3、阿里云OSS等

### 6.2 负载均衡

使用负载均衡器来分发请求：

- **Nginx**：反向代理和负载均衡
- **HAProxy**：高可用负载均衡
- **云负载均衡**：如AWS ELB、阿里云SLB等

### 6.3 配置同步

确保多台服务器的配置文件保持一致，可以使用配置管理工具：

- **Ansible**：配置管理和自动化
- **Chef**：自动化配置管理
- **Puppet**：配置管理

## 7. 监控和维护

### 7.1 日志管理

- **系统日志**：服务启动、停止、错误等信息
- **任务日志**：任务执行状态和结果
- **访问日志**：API请求和响应

### 7.2 监控工具

推荐使用以下监控工具：

- **Prometheus**：监控系统指标
- **Grafana**：可视化监控数据
- **ELK Stack**：日志收集和分析

### 7.3 定期维护

- **清理过期文件**：定期清理archive目录中的过期文件
- **更新依赖包**：定期更新依赖包到最新版本
- **备份配置**：定期备份配置文件

## 8. 故障排除

### 8.1 服务启动失败

- **检查Python版本**：确保使用Python 3.8或更高版本
- **检查依赖包**：确保所有依赖包都已安装
- **检查端口占用**：确保端口8000没有被占用
- **检查配置文件**：确保配置文件格式正确

### 8.2 任务执行失败

- **检查优化器路径**：确保优化器可执行文件路径正确
- **检查权限**：确保优化器可执行文件有执行权限
- **检查输入文件**：确保input.gz文件存在且格式正确
- **检查工作目录**：确保工作目录有写入权限

### 8.3 API接口错误

- **检查认证token**：确保使用正确的token
- **检查参数**：确保提供了正确的参数
- **检查任务ID**：确保任务ID存在
- **检查服务状态**：确保服务正常运行

## 9. 安全配置

### 9.1 认证配置

系统支持三种认证方式（JWT、API Key、Bearer Token），推荐在生产环境中启用JWT认证。

#### 9.1.1 JWT密钥配置（与Live Server共享）

JWT认证使用HS256共享密钥，必须与Live Server配置相同的密钥：

```bash
# 设置JWT共享密钥（必须与Live Server一致）
export JWT_SECRET=your_shared_secret
```

在 `config.yaml` 中启用JWT认证：
```yaml
auth:
  enabled: true
  jwt:
    enabled: true
    secret: ${JWT_SECRET}  # 或直接填写密钥
    algorithm: HS256
```

#### 9.1.2 API Key配置（Live Server服务间调用）

用于Live Server向本服务发起的服务间调用：

```bash
# 设置API Key
export ROIS_API_KEY=your_key
```

在 `config.yaml` 中启用API Key认证：
```yaml
auth:
  api_key:
    enabled: true
    key: ${ROIS_API_KEY}  # 或直接填写Key
```

#### 9.1.3 速率限制

速率限制默认启用，每航司每分钟15次请求限制：

```yaml
auth:
  rate_limit:
    enabled: true
    requests_per_minute: 15
```

#### 9.1.4 安全建议

- **定期轮换密钥**：定期更新JWT密钥和API Key以提高安全性
- **限制访问**：只允许特定IP访问API接口
- **环境变量**：生产环境中通过环境变量配置密钥，避免明文写入配置文件

### 9.2 网络安全

- **使用HTTPS**：配置HTTPS以加密传输
- **防火墙**：配置防火墙，只开放必要的端口
- **CORS**：合理配置CORS策略

### 9.3 文件安全

- **文件权限**：设置合理的文件权限
- **文件加密**：对敏感文件进行加密
- **定期清理**：定期清理临时文件

## 10. 性能优化

### 10.1 系统优化

- **调整并发数**：根据服务器性能调整最大并发任务数
- **内存管理**：确保服务器有足够的内存
- **CPU资源**：确保服务器有足够的CPU资源

### 10.2 代码优化

- **缓存**：使用缓存减少重复计算
- **异步处理**：使用异步处理提高并发能力
- **数据库优化**：如果使用数据库，优化数据库查询

### 10.3 网络优化

- **减少网络延迟**：将服务部署在靠近用户的位置
- **使用CDN**：使用CDN加速静态资源
- **压缩数据**：压缩传输数据以减少带宽使用

## 11. 总结

优化引擎调度工具的部署过程相对简单，主要包括环境准备、安装依赖、配置文件和启动服务等步骤。通过合理的部署和配置，可以确保服务的稳定运行和良好的性能。

在部署过程中，需要注意以下几点：

1. 确保环境满足系统要求
2. 正确配置配置文件
3. 合理设置文件路径和权限
4. 配置适当的并发数和超时时间
5. 定期监控和维护服务

通过以上步骤，可以成功部署和运行优化引擎调度工具，为企业内部的优化任务提供统一的管理和调度服务。