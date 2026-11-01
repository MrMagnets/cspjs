#!/usr/bin/env bash
# 一键启动开发环境（macOS / Linux）
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "[1/2] 启动后端 http://127.0.0.1:8000 ..."
(cd "$root/backend" && python -m uvicorn app.main:app --reload --port 8000) &
BACKEND_PID=$!

sleep 2

echo "[2/2] 启动前端 http://127.0.0.1:5173 ..."
(cd "$root/frontend" && pnpm dev) &
FRONTEND_PID=$!

trap 'kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true' INT TERM
wait
