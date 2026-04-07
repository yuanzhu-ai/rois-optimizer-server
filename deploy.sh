#!/bin/bash
# ROIS Optimizer Server 部署脚本
# 用法：
#   1. 在开发机打包：  ./deploy.sh pack
#   2. 传到目标服务器： scp rois-optimizer-server.tar.gz user@server:/opt/
#   3. 在目标服务器：   tar xzf rois-optimizer-server.tar.gz && cd rois-optimizer-server && ./deploy.sh install

set -e

APP_NAME="rois-optimizer-server"
APP_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVICE_PORT=8000

# ============ 打包 ============
# 先调 build.sh 用 PyInstaller 编译出可执行文件，再把
# 二进制 + 配置示例 + 运行时 deploy.sh 打成 tar.gz。
# 发布包不包含任何 Python 源码。
pack() {
    cd "$APP_DIR"

    echo "==> 步骤 1/2：编译可执行文件..."
    if [ ! -f "build.sh" ]; then
        echo "错误：未找到 build.sh"
        exit 1
    fi
    bash build.sh

    if [ ! -f "dist/optimize_server" ]; then
        echo "错误：dist/optimize_server 不存在，构建失败"
        exit 1
    fi

    echo "==> 步骤 2/2：打包发布产物..."
    PACK_DIR=$(mktemp -d)
    TARGET="$PACK_DIR/$APP_NAME"
    mkdir -p "$TARGET"

    # 二进制
    cp dist/optimize_server "$TARGET/optimize_server"
    chmod +x "$TARGET/optimize_server"

    # 配置示例（不含真实密钥/路径，由客户端复制为 config.yaml 后自行修改）
    if [ -f "src/config/config.yaml.example" ]; then
        cp src/config/config.yaml.example "$TARGET/config.yaml.example"
    elif [ -f "config.yaml" ]; then
        cp config.yaml "$TARGET/config.yaml.example"
    fi

    # 运行时 deploy.sh（来自 dist-pack/，已是二进制运行模式，不含 venv/pip 逻辑）
    if [ ! -f "dist-pack/deploy.sh" ]; then
        echo "错误：未找到 dist-pack/deploy.sh"
        exit 1
    fi
    cp dist-pack/deploy.sh "$TARGET/deploy.sh"
    chmod +x "$TARGET/deploy.sh"

    # 打包
    TARBALL="$APP_DIR/dist-pack/$APP_NAME.tar.gz"
    mkdir -p "$APP_DIR/dist-pack"
    tar czf "$TARBALL" -C "$PACK_DIR" "$APP_NAME"
    rm -rf "$PACK_DIR"

    SIZE=$(du -h "$TARBALL" | cut -f1)
    echo "==> 打包完成：$TARBALL ($SIZE)"
    echo ""
    echo "发布包内容（无源码）："
    echo "  optimize_server         单文件可执行（PyInstaller onefile）"
    echo "  config.yaml.example     配置示例"
    echo "  deploy.sh               运行时管理脚本（install/start/stop/restart/status）"
    echo ""
    echo "下一步（DEPLOY_DIR 替换为客户机部署目录）："
    echo "  scp $TARBALL user@客户机:<DEPLOY_DIR>/"
    echo "  ssh user@客户机"
    echo "  cd <DEPLOY_DIR> && tar xzf $APP_NAME.tar.gz && cd $APP_NAME"
    echo "  cp config.yaml.example config.yaml && vi config.yaml"
    echo "  ./deploy.sh install && ./deploy.sh start"
}

# ============ 安装 ============
install() {
    echo "==> 安装 $APP_NAME ..."
    cd "$APP_DIR"

    # 检查 Python
    if ! command -v python3 &>/dev/null; then
        echo "错误：未找到 python3，请先安装 Python 3.8+"
        exit 1
    fi

    PYTHON_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    echo "    Python 版本: $PYTHON_VER"

    # 创建虚拟环境
    if [ ! -d "venv" ]; then
        echo "==> 创建虚拟环境..."
        python3 -m venv venv
    fi
    source venv/bin/activate

    # 安装依赖
    echo "==> 安装依赖..."
    pip install --upgrade pip -q
    pip install -r requirements.txt -q

    # 创建运行时目录
    mkdir -p workspace finished archive temp logs

    # 提示配置
    echo ""
    echo "==> 安装完成！"
    echo ""
    echo "请根据实际环境编辑 config.yaml："
    echo "  vi $APP_DIR/config.yaml"
    echo ""
    echo "需要设置的环境变量（写入 .env 文件或 export）："
    echo "  export JWT_SECRET=<与 Live Server 共享的密钥>"
    echo "  export ROIS_API_KEY=<API Key>"
    echo ""
    echo "启动服务："
    echo "  ./deploy.sh start"
}

# ============ 启动 ============
start() {
    cd "$APP_DIR"
    source venv/bin/activate 2>/dev/null || true

    # 加载 .env（如果存在）
    if [ -f .env ]; then
        echo "==> 加载 .env 环境变量..."
        set -a; source .env; set +a
    fi

    # 检查端口占用
    if lsof -i :$SERVICE_PORT &>/dev/null 2>&1 || ss -tlnp | grep -q ":$SERVICE_PORT "; then
        echo "警告：端口 $SERVICE_PORT 已被占用"
        echo "  使用 ./deploy.sh stop 停止旧进程，或修改 config.yaml 中的端口"
        exit 1
    fi

    echo "==> 启动服务 (端口 $SERVICE_PORT)..."
    nohup python3 main.py > logs/server.log 2>&1 &
    SERVER_PID=$!
    echo $SERVER_PID > .server.pid

    # 等待启动
    sleep 2
    if kill -0 $SERVER_PID 2>/dev/null; then
        echo "==> 服务已启动 (PID: $SERVER_PID)"
        echo "    日志: tail -f $APP_DIR/logs/server.log"
        echo "    验证: curl http://localhost:$SERVICE_PORT/health"
    else
        echo "错误：服务启动失败，查看日志："
        tail -20 logs/server.log
        exit 1
    fi
}

# ============ 停止 ============
stop() {
    cd "$APP_DIR"
    if [ -f .server.pid ]; then
        PID=$(cat .server.pid)
        if kill -0 $PID 2>/dev/null; then
            echo "==> 停止服务 (PID: $PID)..."
            kill $PID
            sleep 2
            # 如果还没退出，强制终止
            if kill -0 $PID 2>/dev/null; then
                kill -9 $PID
            fi
            echo "==> 服务已停止"
        else
            echo "服务未运行"
        fi
        rm -f .server.pid
    else
        echo "未找到 PID 文件，尝试查找进程..."
        pkill -f "python3 main.py" 2>/dev/null && echo "==> 服务已停止" || echo "服务未运行"
    fi
}

# ============ 状态 ============
status() {
    cd "$APP_DIR"
    if [ -f .server.pid ]; then
        PID=$(cat .server.pid)
        if kill -0 $PID 2>/dev/null; then
            echo "服务运行中 (PID: $PID)"
            curl -s "http://localhost:$SERVICE_PORT/health" 2>/dev/null && echo "" || echo "  (健康检查失败)"
            return 0
        fi
    fi
    echo "服务未运行"
    return 1
}

# ============ 重启 ============
restart() {
    stop
    sleep 1
    start
}

# ============ 入口 ============
case "${1:-help}" in
    pack)    pack ;;
    install) install ;;
    start)   start ;;
    stop)    stop ;;
    restart) restart ;;
    status)  status ;;
    *)
        echo "用法: $0 {pack|install|start|stop|restart|status}"
        echo ""
        echo "  pack     在开发机打包部署文件"
        echo "  install  在目标服务器安装（创建 venv + 安装依赖）"
        echo "  start    启动服务（后台运行）"
        echo "  stop     停止服务"
        echo "  restart  重启服务"
        echo "  status   查看服务状态"
        ;;
esac
