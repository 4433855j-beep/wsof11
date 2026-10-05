#!/usr/bin/env bash
# macOS / Linux 실행 스크립트
set -e
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  echo "[PC Link] 최초 설치 중입니다. 잠시 기다려 주세요..."
  python3 -m venv .venv
  .venv/bin/python -m pip install --upgrade pip
  .venv/bin/python -m pip install -r requirements.txt -r requirements-optional.txt
fi
exec .venv/bin/python -m pclink "$@"
