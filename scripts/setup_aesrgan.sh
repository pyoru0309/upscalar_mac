#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_DIR="${UPSCALER_AESRGAN_REPO:-"$ROOT/external/A-ESRGAN"}"
MODEL_DIR="$ROOT/models"

mkdir -p "$ROOT/external" "$MODEL_DIR"

if [ ! -d "$REPO_DIR/.git" ]; then
  git clone https://github.com/stroking-fishes-ml-corp/A-ESRGAN "$REPO_DIR"
fi

python3 "$ROOT/scripts/patch_aesrgan_compat.py" "$REPO_DIR"

curl -L \
  -o "$MODEL_DIR/A_ESRGAN_Multi.pth" \
  https://github.com/stroking-fishes-ml-corp/A-ESRGAN/releases/download/v1.0.0/A_ESRGAN_Multi.pth

curl -L \
  -o "$MODEL_DIR/A_ESRGAN_Single.pth" \
  https://github.com/stroking-fishes-ml-corp/A-ESRGAN/releases/download/v1.0.0/A_ESRGAN_Single.pth

cat <<EOF
A-ESRGAN files are ready.

export UPSCALER_AESRGAN_REPO="$REPO_DIR"
export UPSCALER_AESRGAN_MODEL="$MODEL_DIR/A_ESRGAN_Multi.pth"
export UPSCALER_AESRGAN_MULTI_MODEL="$MODEL_DIR/A_ESRGAN_Multi.pth"
export UPSCALER_AESRGAN_SINGLE_MODEL="$MODEL_DIR/A_ESRGAN_Single.pth"
EOF
