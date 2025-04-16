#!/bin/bash

# 设置项目根目录
PROJECT_DIR="/home/devbox/project"
cd "$PROJECT_DIR"

# 激活虚拟环境
source venv/bin/activate

# 安装依赖包
pip install -r requirements.txt

# 启动应用
python3 app.py