#!/bin/bash
cd "$(dirname "$0")" || exit 1
python3 -m pip install -r requirements.txt || exit 1
(sleep 2; open http://127.0.0.1:3000/) &
python3 run.py
