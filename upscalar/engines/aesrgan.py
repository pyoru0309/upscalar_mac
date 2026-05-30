from __future__ import annotations

import glob
from pathlib import Path

from upscalar import settings
from upscalar.engines.base import EngineSpec, UpscaleRequest, UpscaleResult
from upscalar.engines.utils import run_command


class AESRGANUpscaler:
    spec = EngineSpec(
        id="aesrgan",
        name="A-ESRGAN",
        description="Attention U-Net discriminator 系の4x GANアップスケーラーです。",
        setup_hint="UPSCALAR_AESRGAN_REPO と UPSCALAR_AESRGAN_MULTI_MODEL / UPSCALAR_AESRGAN_SINGLE_MODEL を設定してください。",
    )

    def is_available(self) -> bool:
        return self._script_path().exists() and any(
            path.exists()
            for path in (
                settings.AESRGAN_MULTI_MODEL,
                settings.AESRGAN_SINGLE_MODEL,
                settings.AESRGAN_MODEL,
            )
        )

    def availability_message(self) -> str:
        missing = []
        if not self._script_path().exists():
            missing.append(f"repo: {settings.AESRGAN_REPO}")
        available_models = [
            name
            for name, path in (
                ("multi", settings.AESRGAN_MULTI_MODEL),
                ("single", settings.AESRGAN_SINGLE_MODEL),
                ("custom", settings.AESRGAN_MODEL),
            )
            if path.exists()
        ]
        if not available_models:
            missing.append(f"models: {settings.MODELS_DIR}/A_ESRGAN_*.pth")
        if missing:
            return "未設定: " + ", ".join(missing)
        return "available: " + ", ".join(available_models)

    def upscale(self, request: UpscaleRequest) -> UpscaleResult:
        script = self._script_path()
        model_name = str(request.options.get("aesrgan_model", "multi"))
        model_path = settings.aesrgan_model_path(model_name)
        if not script.exists() or not model_path.exists():
            raise RuntimeError(self.availability_message())

        request.output_dir.mkdir(parents=True, exist_ok=True)
        job_id = str(request.options.get("job_id", "")).strip()
        suffix = f"aesrgan_{model_name}_{job_id}" if job_id else f"aesrgan_{model_name}"
        args = [
            settings.AESRGAN_PYTHON,
            str(script),
            "--model_path",
            str(model_path),
            "--input",
            str(request.input_path),
            "--output",
            str(request.output_dir),
            "--suffix",
            suffix,
            "--tile",
            str(max(0, int(request.tile))),
        ]
        if request.half and self._supports_half():
            args.append("--half")

        log = run_command(args, cwd=settings.AESRGAN_REPO, cancel_token=request.cancel_token)
        output_path = self._find_output(request.output_dir, request.input_path.stem, suffix)
        if output_path is None:
            raise RuntimeError(f"A-ESRGAN completed but no output was found.\n{log}")
        return UpscaleResult(output_path=output_path, log=log)

    def _script_path(self) -> Path:
        return settings.AESRGAN_REPO / "inference_aesrgan.py"

    @staticmethod
    def _supports_half() -> bool:
        try:
            import torch

            return bool(torch.cuda.is_available())
        except Exception:
            return False

    @staticmethod
    def _find_output(output_dir: Path, stem: str, suffix: str) -> Path | None:
        matches = sorted(glob.glob(str(output_dir / f"{stem}_{suffix}.*")))
        return Path(matches[0]) if matches else None
