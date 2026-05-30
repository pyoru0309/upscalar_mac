from __future__ import annotations

import os
import platform
import shutil
import sys

from upscaler import settings
from upscaler.registry import build_registry


def diagnostics_markdown() -> str:
    rows = [
        ("Python", sys.version.replace("\n", " ")),
        ("Executable", sys.executable),
        ("Platform", f"{platform.system()} {platform.release()} ({platform.machine()})"),
        ("Project root", str(settings.PROJECT_ROOT)),
        ("Outputs", str(settings.OUTPUTS_DIR)),
        ("Models", str(settings.MODELS_DIR)),
        ("External", str(settings.EXTERNAL_DIR)),
        ("UPSCALER_REALESRGAN_BIN", settings.REALESRGAN_BIN),
        ("UPSCALER_AESRGAN_REPO", str(settings.AESRGAN_REPO)),
        ("UPSCALER_SPANDREL_MODEL_DIR", str(settings.SPANDREL_MODEL_DIR)),
        ("realesrgan-ncnn-vulkan on PATH", shutil.which(settings.REALESRGAN_BIN) or "-"),
    ]

    torch_info = _torch_info()
    rows.extend(torch_info)
    rows.extend(_memory_lines())

    for engine in build_registry().values():
        rows.append((f"Engine: {engine.spec.name}", engine.availability_message()))

    table = ["| Item | Value |", "| --- | --- |"]
    table.extend(f"| {key} | {value} |" for key, value in rows)
    return "\n".join(table)


def _torch_info() -> list[tuple[str, str]]:
    try:
        import torch
    except ImportError:
        return [("Torch", "not installed")]

    cuda_available = bool(torch.cuda.is_available())
    values = [
        ("Torch", getattr(torch, "__version__", "unknown")),
        ("CUDA available", str(cuda_available)),
    ]
    if cuda_available:
        values.append(("CUDA device", torch.cuda.get_device_name(0)))
    elif os.getenv("CUDA_VISIBLE_DEVICES"):
        values.append(("CUDA_VISIBLE_DEVICES", os.getenv("CUDA_VISIBLE_DEVICES", "")))
    try:
        values.append(("MPS available", str(bool(torch.backends.mps.is_available()))))
    except Exception:
        pass
    return values


def _format_bytes(n: int) -> str:
    return f"{n / (1024 ** 3):.2f} GiB"


def _memory_lines() -> list[tuple[str, str]]:
    try:
        import torch
    except ImportError:
        return []
    lines: list[tuple[str, str]] = []
    try:
        if torch.backends.mps.is_available():
            lines.append(("MPS allocated (live)", _format_bytes(torch.mps.current_allocated_memory())))
            lines.append(("MPS reserved (driver)", _format_bytes(torch.mps.driver_allocated_memory())))
    except Exception:
        pass
    return lines


def release_memory() -> str:
    # キャッシュされた未使用GPUメモリを解放する。ライブのテンソルは解放できないが、
    # 推論の合間に呼ぶと driver 予約分(キャッシュプール)を OS へ返せる。
    import gc

    try:
        import torch
    except ImportError:
        gc.collect()
        return "メモリを解放しました（torch 未導入のため Python GC のみ実行）。"

    has_mps = False
    try:
        has_mps = bool(torch.backends.mps.is_available())
    except Exception:
        has_mps = False

    before = None
    if has_mps:
        try:
            before = torch.mps.driver_allocated_memory()
        except Exception:
            before = None

    gc.collect()
    if has_mps:
        try:
            torch.mps.empty_cache()
        except Exception:
            pass
    try:
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        pass

    if before is not None:
        try:
            after = torch.mps.driver_allocated_memory()
            freed = max(0, before - after)
            return (
                f"メモリを解放しました。MPS 予約: {_format_bytes(before)} → {_format_bytes(after)} "
                f"（解放 {_format_bytes(freed)}）"
            )
        except Exception:
            pass
    return "メモリを解放しました（gc + empty_cache を実行）。"
