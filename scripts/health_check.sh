#!/usr/bin/env bash
set -euo pipefail

curl -sf http://localhost:8501/healthz
curl -sf http://localhost:9090
