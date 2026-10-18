#!/usr/bin/env bash
set -euo pipefail
date -u +%FT%TZ
sudo docker ps --format '{{.Names}} {{.Image}}'
for i in $(seq 1 180); do
  date -u +%FT%TZ
  nvidia-smi --query-compute-apps=pid,process_name,used_gpu_memory --format=csv,noheader
  sleep 5
done
