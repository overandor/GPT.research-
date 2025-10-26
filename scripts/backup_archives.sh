#!/usr/bin/env bash
set -euo pipefail

SRC_DIR=${1:-/data}
DEST_DIR=${2:-/backups}

mkdir -p "${DEST_DIR}"
cp -r "${SRC_DIR}"/*.json "${DEST_DIR}"/ 2>/dev/null || true
