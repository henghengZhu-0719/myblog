#!/bin/bash

# 获取当前脚本所在目录
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# 颜色定义
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== 启动博客项目 ===${NC}"

# 1. 启动后端
echo -e "${GREEN}正在启动后端服务 (Uvicorn)...${NC}"
# 使用 nohup 在后台运行，并将日志输出到 backend.log
source "$DIR/.venv/bin/activate"

cd "$DIR"
nohup uv run uvicorn main:app --reload --host 0.0.0.0 --port 8001 > "$DIR/backend.log" 2>&1 &
BACKEND_PID=$!
echo "后端已在后台启动，PID: $BACKEND_PID"

# 2. 启动前端
echo -e "${GREEN}正在启动前端服务 (Vite)...${NC}"
cd "$DIR/frontend"
# 使用 nohup 在后台运行，并将日志输出到 frontend.log
nohup npm run dev > "$DIR/frontend.log" 2>&1 &
FRONTEND_PID=$!
echo "前端已在后台启动，PID: $FRONTEND_PID"

echo -e "${GREEN}=== 服务已全部启动 ===${NC}"
echo "后端日志: $DIR/backend.log"
echo "前端日志: $DIR/frontend.log"
echo -e "${GREEN}请访问: http://localhost:5173${NC}"
echo "停止服务请运行: kill $BACKEND_PID $FRONTEND_PID"

# 可选：如果你想让脚本在前台运行并同时监控两个进程，可以使用 wait
# wait $BACKEND_PID $FRONTEND_PID
