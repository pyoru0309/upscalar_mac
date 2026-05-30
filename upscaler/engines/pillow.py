from __future__ import annotations

from upscaler.engines.base import EngineSpec, UpscaleRequest, UpscaleResult, output_path_for


class PillowLanczosUpscaler:
    spec = EngineSpec(
        id="pillow_lanczos",
        name="Pillow Lanczos",
        description="AIではない確認用の高速リサイズです。",
        setup_hint="requirements.txt の pillow が入っていれば利用できます。",
    )

    def is_available(self) -> bool:
        try:
            import PIL  # noqa: F401
        except ImportError:
            return False
        return True

    def availability_message(self) -> str:
        return "available" if self.is_available() else "Pillow が未インストールです。"

    def upscale(self, request: UpscaleRequest) -> UpscaleResult:
        from PIL import Image

        scale = max(1, int(request.scale))
        output_path = output_path_for(request, f"lanczos_x{scale}", ".png")
        with Image.open(request.input_path) as image:
            resized = image.resize(
                (image.width * scale, image.height * scale),
                Image.Resampling.LANCZOS,
            )
            resized.save(output_path)
        return UpscaleResult(output_path=output_path, log=f"Saved {output_path}")
