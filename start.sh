#!/usr/bin/env bash
#
# 一键启动 API Search Agent（本地开发/测试）
#
#   ./start.sh            # 自检并启动前后端
#   ./start.sh rebuild    # 先重建向量索引再启动（上传新文档后用）
#
# 首次运行会自动补齐：后端 venv、Python 依赖、前端依赖、本地 embedding 模型、向量索引。
# Ctrl+C 同时停止前后端。
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

PY="backend/.venv/bin/python"
PIP="backend/.venv/bin/pip"
PYPI_MIRROR="https://pypi.tuna.tsinghua.edu.cn/simple"

MODEL_DIR="storage/models/fast-bge-small-zh-v1.5"
MODEL_TGZ_URL="https://storage.googleapis.com/qdrant-fastembed/fast-bge-small-zh-v1.5.tar.gz"
VECTORS="storage/vectors.npz"

BACKEND_HOST="127.0.0.1"
BACKEND_PORT="${BACKEND_PORT:-8000}"     # 可用环境变量覆盖：BACKEND_PORT=8800 ./start.sh
FRONTEND_PORT="${FRONTEND_PORT:-3001}"   # 避开常被占用的 5173（如其它前端项目）

log()  { printf "\033[1;36m[start]\033[0m %s\n" "$*"; }
warn() { printf "\033[1;33m[start]\033[0m %s\n" "$*"; }

# 从指定端口起向上找一个空闲端口，避免与已占用端口冲突
find_free_port() {
  local port="$1"
  while lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; do
    port=$((port + 1))
  done
  printf "%s" "$port"
}

# --- 1. 后端 venv + 依赖 -----------------------------------------------------
if [ ! -x "backend/.venv/bin/uvicorn" ]; then
  log "创建后端虚拟环境并安装依赖（首次较慢）..."
  python3 -m venv backend/.venv
  "$PIP" install -q --upgrade pip
  "$PIP" install -q -i "$PYPI_MIRROR" -r backend/requirements.txt
fi

# --- 2. 后端 .env ------------------------------------------------------------
if [ ! -f "backend/.env" ]; then
  warn "backend/.env 不存在，已从 .env.example 复制；如需 LLM 改写请填入 GEMINI_API_KEY 并设 ENABLE_LLM_AGENT=true"
  cp backend/.env.example backend/.env
fi

# --- 3. 本地 embedding 模型（国内走 GCS，绕开被墙的 HuggingFace）-------------
if [ ! -d "$MODEL_DIR" ]; then
  log "下载本地 embedding 模型 bge-small-zh-v1.5（~52MB）..."
  mkdir -p storage/models
  curl -fL --connect-timeout 20 -o storage/models/_model.tar.gz "$MODEL_TGZ_URL"
  tar -xzf storage/models/_model.tar.gz -C storage/models
  rm -f storage/models/_model.tar.gz
  log "模型就绪：$MODEL_DIR"
fi

# --- 4. 向量索引 -------------------------------------------------------------
if [ "${1:-}" = "rebuild" ]; then
  warn "rebuild 模式：删除旧向量索引"
  rm -f "$VECTORS" "${VECTORS%.npz}.json"
fi
if [ ! -f "$VECTORS" ]; then
  log "构建向量索引（首次约 3 分钟，CPU 嵌入 1781 个 API）..."
  PYTHONPATH=backend "$PY" backend/build_vectors.py
fi

# --- 5. 前端依赖 -------------------------------------------------------------
if [ ! -d "frontend/node_modules" ]; then
  log "安装前端依赖..."
  npm --prefix frontend install
fi

# --- 6. 解析空闲端口并同时启动前后端 ----------------------------------------
desired_backend="$BACKEND_PORT"
desired_frontend="$FRONTEND_PORT"
BACKEND_PORT="$(find_free_port "$BACKEND_PORT")"
FRONTEND_PORT="$(find_free_port "$FRONTEND_PORT")"
if [ "$BACKEND_PORT" != "$desired_backend" ]; then
  warn "后端端口 $desired_backend 被占用，自动改用 $BACKEND_PORT"
fi
if [ "$FRONTEND_PORT" != "$desired_frontend" ]; then
  warn "前端端口 $desired_frontend 被占用，自动改用 $FRONTEND_PORT"
fi

# 让前后端端口保持一致：后端放行该前端来源(CORS)，前端指向该后端 API
export CORS_ORIGINS="http://localhost:${FRONTEND_PORT},http://127.0.0.1:${FRONTEND_PORT}"
export VITE_API_BASE_URL="http://127.0.0.1:${BACKEND_PORT}/api"

log "启动后端 (uvicorn :$BACKEND_PORT) + 前端 (vite :$FRONTEND_PORT) ..."
PYTHONPATH=backend backend/.venv/bin/uvicorn app.main:app \
  --app-dir backend --host "$BACKEND_HOST" --port "$BACKEND_PORT" &
BACKEND_PID=$!

npm --prefix frontend run dev -- --port "$FRONTEND_PORT" --strictPort &
FRONTEND_PID=$!

# 递归杀掉进程及其子孙（npm 会派生 vite，uvicorn 可能有 reloader 子进程）
kill_tree() {
  local pid="$1"
  local child
  for child in $(pgrep -P "$pid" 2>/dev/null); do
    kill_tree "$child"
  done
  kill "$pid" 2>/dev/null || true
}

cleaned=0
cleanup() {
  [ "$cleaned" = "1" ] && return
  cleaned=1
  log "正在停止前后端 ..."
  kill_tree "$FRONTEND_PID"
  kill_tree "$BACKEND_PID"
  # 兜底：按命令特征清理本项目残留进程（限定 APISearch，不影响其它项目）
  pkill -f "uvicorn app.main:app --app-dir backend" 2>/dev/null || true
  pkill -f "APISearch/frontend/node_modules/.bin/vite" 2>/dev/null || true
  # 宽限后对仍存活的进程升级为 SIGKILL，确保不残留
  sleep 1
  pkill -9 -f "uvicorn app.main:app --app-dir backend" 2>/dev/null || true
  pkill -9 -f "APISearch/frontend/node_modules/.bin/vite" 2>/dev/null || true
  wait "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
}
trap cleanup INT TERM EXIT

printf "\n"
log "后端 API:  http://${BACKEND_HOST}:${BACKEND_PORT}/api/health"
log "前端页面:  http://${BACKEND_HOST}:${FRONTEND_PORT}"
log "按 Ctrl+C 停止"
printf "\n"

# 任一进程退出即结束（cleanup 由 trap 负责）。用轮询以兼容 macOS 自带的 bash 3.2。
while kill -0 "$BACKEND_PID" 2>/dev/null && kill -0 "$FRONTEND_PID" 2>/dev/null; do
  sleep 1
done
