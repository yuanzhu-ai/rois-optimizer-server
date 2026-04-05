# 项目记忆文件

## 版本更新流程

每次编译之后，会自动更新 `git.properties` 文件内容，确保版本信息与最新的 git 提交保持一致。

### 编译流程：

1. **Windows 编译**：
   ```bash
   # 运行编译脚本
   build.bat
   ```

2. **Linux 编译**：
   ```bash
   # 运行编译脚本
   ./build.sh
   ```

3. **Docker 跨平台编译**：
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

### 版本信息生成：

编译时，`generate_git_properties.py` 脚本会自动生成 `git.properties` 文件，包含以下信息：

```properties
# Git 提交信息
git.commit.id=<完整的 git commit id>
git.commit.id.abbrev=<git commit id 前7位>
git.commit.author.name=<提交作者>
git.commit.time=<提交时间>
build.timestamp=<构建时间戳>
```

### 版本信息读取：

服务启动时，`src/version.py` 文件会读取 `git.properties` 文件中的信息，并通过 API 接口展示：

- 访问 `GET /api/system/info` 接口，可以查看当前部署的版本信息
- 版本信息包含：服务名称、完整版本信息、Git 提交 ID、提交作者、构建时间戳、服务状态

### 示例响应：

```json
{
  "service": "优化引擎调度工具",
  "version": "1.0.0-746c7d6-2026-04-03 17:30:00",
  "git_commit_id": "746c7d6",
  "commit_author": "yuan.zhu",
  "build_timestamp": "2026-04-03 17:30:00",
  "status": "running"
}
```

## 其他注意事项

- 确保每次编译时都执行 `generate_git_properties.py` 脚本，以生成最新的版本信息
- 版本号（VERSION）在 `src/version.py` 文件中定义，可以根据项目的实际情况进行调整
- `git.properties` 文件会在编译时自动生成，不需要提交到 Git 仓库
- 可执行文件部署时，`git.properties` 文件会被打包到可执行文件中，确保版本信息的完整性
