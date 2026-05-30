from __future__ import annotations

import shlex

from upscaler.engines.base import EngineSpec, UpscaleRequest, UpscaleResult, output_path_for
from upscaler.engines.utils import run_command


class ExternalCommandUpscaler:
    spec = EngineSpec(
        id="external_command",
        name="External Command",
        description="MSA-ESRGANや独自推論スクリプトなどをCLIとして接続します。",
        setup_hint='例: python inference.py --input "{input}" --output "{output}" --scale {scale} --tile {tile}',
    )

    def is_available(self) -> bool:
        return True

    def availability_message(self) -> str:
        return "command template required at runtime"

    def upscale(self, request: UpscaleRequest) -> UpscaleResult:
        if not request.custom_command.strip():
            raise RuntimeError("External Command を使うにはコマンドテンプレートが必要です。")

        output_path = output_path_for(request, f"external_x{request.scale}", ".png")
        command = request.custom_command.format(
            input=str(request.input_path),
            output=str(output_path),
            scale=int(request.scale),
            tile=int(request.tile),
        )
        log = run_command(shlex.split(command), cancel_token=request.cancel_token)
        if not output_path.exists():
            raise RuntimeError(f"Command completed but output file was not created: {output_path}\n{log}")
        return UpscaleResult(output_path=output_path, log=log)
