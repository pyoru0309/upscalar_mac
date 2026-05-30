from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUTS_DIR = PROJECT_ROOT / "inputs"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
MODELS_DIR = PROJECT_ROOT / "models"
EXTERNAL_DIR = PROJECT_ROOT / "external"
HISTORY_PATH = OUTPUTS_DIR / "history.jsonl"
PREFS_PATH = PROJECT_ROOT / "user_prefs.json"
DOCS_DIR = PROJECT_ROOT / "docs"


def _default_realesrgan_bin() -> str:
    bundled = EXTERNAL_DIR / "realesrgan-ncnn-vulkan" / "realesrgan-ncnn-vulkan"
    if bundled.exists():
        return str(bundled)
    return "realesrgan-ncnn-vulkan"


REALESRGAN_BIN = os.getenv("UPSCALER_REALESRGAN_BIN", _default_realesrgan_bin())
REALESRGAN_MODEL_DIR = Path(
    os.getenv("UPSCALER_REALESRGAN_MODEL_DIR", EXTERNAL_DIR / "realesrgan-ncnn-vulkan" / "models")
)
AESRGAN_REPO = Path(os.getenv("UPSCALER_AESRGAN_REPO", EXTERNAL_DIR / "A-ESRGAN"))
AESRGAN_MODEL = Path(os.getenv("UPSCALER_AESRGAN_MODEL", MODELS_DIR / "A_ESRGAN_Multi.pth"))
AESRGAN_MULTI_MODEL = Path(os.getenv("UPSCALER_AESRGAN_MULTI_MODEL", MODELS_DIR / "A_ESRGAN_Multi.pth"))
AESRGAN_SINGLE_MODEL = Path(os.getenv("UPSCALER_AESRGAN_SINGLE_MODEL", MODELS_DIR / "A_ESRGAN_Single.pth"))
AESRGAN_PYTHON = os.getenv("UPSCALER_AESRGAN_PYTHON", sys.executable)
SPANDREL_MODEL_DIR = Path(os.getenv("UPSCALER_SPANDREL_MODEL_DIR", MODELS_DIR / "spandrel"))
SPANDREL_MODEL = Path(os.getenv("UPSCALER_SPANDREL_MODEL", "")) if os.getenv("UPSCALER_SPANDREL_MODEL") else None


def load_prefs() -> Dict[str, Any]:
    # UI の選択内容を再起動後も保持するための設定ファイル。壊れていても無視して既定に戻す。
    if not PREFS_PATH.exists():
        return {}
    try:
        data = json.loads(PREFS_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def save_prefs(prefs: Dict[str, Any]) -> None:
    try:
        PREFS_PATH.write_text(json.dumps(prefs, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass


def ensure_workspace_dirs() -> None:
    for path in (INPUTS_DIR, OUTPUTS_DIR, MODELS_DIR, EXTERNAL_DIR, SPANDREL_MODEL_DIR):
        path.mkdir(parents=True, exist_ok=True)


SPANDREL_EXTENSIONS = (".pth", ".safetensors", ".pt", ".ckpt")


def spandrel_model_files() -> list[Path]:
    if not SPANDREL_MODEL_DIR.exists():
        return []
    files = [
        path
        for path in sorted(SPANDREL_MODEL_DIR.iterdir())
        if path.is_file() and path.suffix.lower() in SPANDREL_EXTENSIONS
    ]
    return files


def spandrel_model_path(model_name: str = "") -> Path | None:
    name = model_name.strip()
    if name:
        candidate = SPANDREL_MODEL_DIR / name
        if candidate.exists():
            return candidate
        direct = Path(name).expanduser()
        if direct.exists():
            return direct
    if SPANDREL_MODEL and SPANDREL_MODEL.exists():
        return SPANDREL_MODEL
    files = spandrel_model_files()
    return files[0] if files else None


def aesrgan_model_path(model_name: str) -> Path:
    if model_name == "single":
        return AESRGAN_SINGLE_MODEL
    if model_name == "custom":
        return AESRGAN_MODEL
    return AESRGAN_MULTI_MODEL
