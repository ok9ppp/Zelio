#!/bin/bash

# 脚本：启动Flask服务器
# 用法：./start_server.sh [前台|后台]

# 项目根目录
PROJECT_DIR="/home/devbox/project"
# 虚拟环境目录
VENV_DIR="$PROJECT_DIR/venv"
# 应用主文件
APP_FILE="$PROJECT_DIR/app.py"
# 日志文件
LOG_FILE="$PROJECT_DIR/server.log"

# 切换到项目目录
cd "$PROJECT_DIR" || { echo "无法进入项目目录 $PROJECT_DIR"; exit 1; }

# 检查虚拟环境是否存在
if [ ! -d "$VENV_DIR" ]; then
    echo "错误：虚拟环境不存在，路径：$VENV_DIR"
    exit 1
fi

# 停止任何正在运行的服务器实例
echo "停止任何正在运行的服务器实例..."
pkill -f "python $APP_FILE" || pkill -f "python3 $APP_FILE"
sleep 2

# 激活虚拟环境
echo "激活虚拟环境..."
source "$VENV_DIR/bin/activate" || { echo "无法激活虚拟环境"; exit 1; }

# 检查Python版本
PYTHON_VERSION=$(python --version)
echo "使用 $PYTHON_VERSION"

# 启动服务器
if [ "$1" = "后台" ]; then
    echo "在后台启动服务器，日志输出到：$LOG_FILE"
    python "$APP_FILE" > "$LOG_FILE" 2>&1 &
    sleep 2
    # 检查服务器是否成功启动
    if pgrep -f "python $APP_FILE" > /dev/null; then
        echo "服务器成功启动在后台，进程ID: $(pgrep -f "python $APP_FILE")"
        echo "可通过 'tail -f $LOG_FILE' 查看日志"
    else
        echo "服务器启动失败，请检查日志：$LOG_FILE"
    fi
else
    echo "在前台启动服务器..."
    python "$APP_FILE"
fi 