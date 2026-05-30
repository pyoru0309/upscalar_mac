#!/usr/bin/env python3
"""モデル/バックエンドの一括セットアップ。

GitHub からの配布を想定し、必要な重みや実行ファイルをダウンロードする。

使い方:
    python scripts/setup_models.py                 # 既定(spandrel の推奨重み)を取得
    python scripts/setup_models.py spandrel        # Spandrel(MPS) 用の .pth を取得
    python scripts/setup_models.py realesrgan      # Real-ESRGAN ncnn-vulkan を取得
    python scripts/setup_models.py aesrgan         # A-ESRGAN のリポジトリ+重みを取得
    python scripts/setup_models.py all             # すべて取得
    python scripts/setup_models.py spandrel --model realesrgan-x4plus-anime
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = ROOT / "models"
SPANDREL_DIR = MODELS_DIR / "spandrel"

# Spandrel(MPS) で読み込める重み。いずれも公式 GitHub Releases から直接取得できるもの。
# SwinIR は HAT/DAT と同系統の Transformer 系高品質モデルで、写真の実写超解像に強い。
SPANDREL_MODELS = {
    # ESRGAN 系(軽量・高速)
    "realesrgan-x4plus": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth",
    "realesrgan-x4plus-anime": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.2.4/RealESRGAN_x4plus_anime_6B.pth",
    # SwinIR 系(Transformer・高品質)。L は最高品質だが重い。M は実用的なバランス。
    "swinir-realsr-x4-large": "https://github.com/JingyunLiang/SwinIR/releases/download/v0.0/003_realSR_BSRGAN_DFOWMFC_s64w8_SwinIR-L_x4_GAN.pth",
    "swinir-realsr-x4": "https://github.com/JingyunLiang/SwinIR/releases/download/v0.0/003_realSR_BSRGAN_DFO_s64w8_SwinIR-M_x4_GAN.pth",
    "swinir-classical-x4": "https://github.com/JingyunLiang/SwinIR/releases/download/v0.0/001_classicalSR_DF2K_s64w8_SwinIR-M_x4.pth",
}
DEFAULT_SPANDREL_MODEL = "realesrgan-x4plus"

# 直接ダウンロードできる安定したURLが無いため、手動配置を案内するモデル。
MANUAL_SPANDREL_MODELS = {
    "HAT": "https://github.com/XPixelGroup/HAT （公式の配布先(Google Drive等)から .pth を取得）",
    "DAT": "https://github.com/zhengchen1999/DAT （公式の配布先から .pth を取得）",
}


def _download(url: str, dest: Path) -> None:
    if dest.exists() and dest.stat().st_size > 0:
        print(f"skip (already exists): {dest}")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"downloading: {url}")
    tmp = dest.with_name(dest.name + ".part")
    request = urllib.request.Request(url, headers={"User-Agent": "upscaler-setup"})
    with urllib.request.urlopen(request) as response, tmp.open("wb") as fh:
        total = int(response.headers.get("Content-Length") or 0)
        done = 0
        while True:
            chunk = response.read(1 << 20)
            if not chunk:
                break
            fh.write(chunk)
            done += len(chunk)
            if total:
                pct = done * 100 // total
                print(f"\r  {done // (1 << 20)}/{total // (1 << 20)} MiB ({pct}%)", end="", flush=True)
        if total:
            print()
    tmp.replace(dest)
    print(f"saved: {dest}")


def setup_spandrel(model: str | None) -> None:
    if model in (None, "all"):
        targets = SPANDREL_MODELS
    else:
        if model not in SPANDREL_MODELS:
            raise SystemExit(
                f"unknown spandrel model: {model}. choices: {', '.join(SPANDREL_MODELS)}"
            )
        targets = {model: SPANDREL_MODELS[model]}
    for url in targets.values():
        _download(url, SPANDREL_DIR / Path(url).name)
    print(f"Spandrel models are ready in {SPANDREL_DIR}")
    print("\nHAT / DAT など直接DLできないモデルは、配布元から .pth/.safetensors を取得して")
    print(f"{SPANDREL_DIR} に置けば GUI の Spandrel ドロップダウンに表示されます:")
    for name, hint in MANUAL_SPANDREL_MODELS.items():
        print(f"  - {name}: {hint}")


def setup_realesrgan() -> None:
    subprocess.check_call([sys.executable, str(ROOT / "scripts" / "setup_realesrgan_ncnn.py")])


def setup_aesrgan() -> None:
    script = ROOT / "scripts" / "setup_aesrgan.sh"
    subprocess.check_call(["bash", str(script)])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "targets",
        nargs="*",
        default=["spandrel"],
        help="取得対象: spandrel / realesrgan / aesrgan / all (既定: spandrel)",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_SPANDREL_MODEL,
        help=f"spandrel の重み名。choices: {', '.join(SPANDREL_MODELS)} / all (既定: {DEFAULT_SPANDREL_MODEL})",
    )
    args = parser.parse_args()

    targets = set(args.targets)
    if "all" in targets:
        targets = {"spandrel", "realesrgan", "aesrgan"}

    if "spandrel" in targets:
        setup_spandrel(args.model)
    if "realesrgan" in targets:
        setup_realesrgan()
    if "aesrgan" in targets:
        setup_aesrgan()

    print("done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
