#!/bin/sh
cd "$(dirname "$0")/.."
backend/.venv/bin/uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 &
pid=$!
trap 'kill $pid' EXIT INT TERM
cd frontend && npm run dev
