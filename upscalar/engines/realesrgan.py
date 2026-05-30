from __future__ import annotations

from upscalar import settings
from upscalar.engines.base import EngineSpec, UpscaleRequest, UpscaleResult, output_path_for
from upscalar.engines.utils import resolve_executable, run_command


class RealESRGANNcnnUpscaler:
    spec = EngineSpec(
        id="realesrgan_ncnn",
        name="Real-ESRGAN ncnn-vulkan",
        description="導入しやすい標準バックエンドです。写真・アニメ系のモデルを選べます。",
        setup_hint="UPSCALAR_REALESRGAN_BIN で realesrgan-ncnn-vulkan の実行ファイルを指定してください。",
    )

    def is_available(self) -> bool:
        return resolve_executable(settings.REALESRGAN_BIN) is not None

    def availability_message(self) -> str:
        binary = resolve_executable(settings.REALESRGAN_BIN)
        if binary:
            return f"available: {binary}"
        return f"実行ファイルが見つかりません: {settings.REALESRGAN_BIN}"

    def upscale(self, request: UpscaleRequest) -> UpscaleResult:
        binary = resolve_executable(settings.REALESRGAN_BIN)
        if not binary:
            raise RuntimeError(self.availability_message())

        model = str(request.options.get("realesrgan_model", "realesrgan-x4plus"))
        output_path = output_path_for(request, f"{model}_x{request.scale}", ".png")
        args = [
            binary,
            "-i",
            str(request.input_path),
            "-o",
            str(output_path),
            "-n",
            model,
            "-s",
            str(int(request.scale)),
        ]
        if settings.REALESRGAN_MODEL_DIR.exists():
            args.extend(["-m", str(settings.REALESRGAN_MODEL_DIR)])
        if request.tile > 0:
            args.extend(["-t", str(int(request.tile))])
        log = run_command(args, cancel_token=request.cancel_token)
        return UpscaleResult(output_path=output_path, log=log)
