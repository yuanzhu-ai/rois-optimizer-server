#!/bin/bash
# ROIS Optimizer Server 运行时管理脚本（客户端）
#
# 此脚本随单文件可执行版（PyInstaller onefile）一起发布，
# 不依赖 Python / pip / venv。客户机只需要 glibc 与构建机兼容即可。
#
# 用法：
#   ./deploy.sh install      首次安装（创建运行时目录、检查配置）
#   ./deploy.sh start        启动服务
#   ./deploy.sh stop         停止服务
#   ./deploy.sh restart      重启
#   ./deploy.sh status       查看状态

set -e

APP_NAME="rois-optimizer-server"
APP_DIR="$(cd "$(dirname "$0")" && pwd)"
BINARY="$APP_DIR/optimize_server"
SERVICE_PORT=8000

# ============ 安装 ============
install() {
    echo "==> 安装 $APP_NAME ..."
    cd "$APP_DIR"

    if [ ! -f "$BINARY" ]; then
        echo "错误：未找到可执行文件 $BINARY"
        exit 1
    fi
    chmod +x "$BINARY"

    # 配置文件检查
    if [ ! -f "config.yaml" ]; then
        if [ -f "config.yaml.example" ]; then
            echo "==> 未找到 config.yaml，已从示例复制一份："
            cp config.yaml.example config.yaml
            echo "    请编辑 $APP_DIR/config.yaml 后再启动服务"
        else
            echo "警告：未找到 config.yaml 与 config.yaml.example，将使用内置默认配置"
        fi
    fi

    # 创建运行时目录
    mkdir -p workspace finished archive temp logs

    echo ""
    echo "==> 安装完成"
    echo ""
    echo "需要的环境变量（写入 .env 或 export）："
    echo "  JWT_SECRET=<与 Live Server 共享的密钥>"
    echo "  ROIS_API_KEY=<API Key>"
    echo ""
    echo "启动服务： ./deploy.sh start"
}

# ============ 启动 ============
start() {
    cd "$APP_DIR"

    if [ ! -x "$BINARY" ]; then
        echo "错误：可执行文件不存在或无执行权限：$BINARY"
        exit 1
    fi

    # 加载 .env（如果存在）
    if [ -f .env ]; then
        echo "==> 加载 .env 环境变量..."
        set -a; source .env; set +a
    fi

    # 让 config 模块读取本目录下的 config.yaml
    export ROIS_CONFIG_PATH="$APP_DIR/config.yaml"

    # 检查端口占用
    if command -v ss &>/dev/null && ss -tlnp 2>/dev/null | grep -q ":$SERVICE_PORT "; then
        echo "警告：端口 $SERVICE_PORT 已被占用"
        echo "  使用 ./deploy.sh stop 停止旧进程，或修改 config.yaml 中的端口"
        exit 1
    fi

    mkdir -p logs
    echo "==> 启动服务 (端口 $SERVICE_PORT)..."
    nohup "$BINARY" > logs/server.log 2>&1 &
    SERVER_PID=$!
    echo $SERVER_PID > .server.pid

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
        pkill -f "optimize_server" 2>/dev/null && echo "==> 服务已停止" || echo "服务未运行"
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
    install) install ;;
    start)   start ;;
    stop)    stop ;;
    restart) restart ;;
    status)  status ;;
    *)
        echo "用法: $0 {install|start|stop|restart|status}"
        echo ""
        echo "  install  首次安装（创建运行时目录、复制配置示例）"
        echo "  start    启动服务（后台运行）"
        echo "  stop     停止服务"
        echo "  restart  重启服务"
        echo "  status   查看服务状态"
        ;;
esac
