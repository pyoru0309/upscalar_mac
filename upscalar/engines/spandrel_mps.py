from __future__ import annotations

from upscalar import settings
from upscalar.engines.base import EngineSpec, UpscaleRequest, UpscaleResult, output_path_for


class SpandrelMPSUpscaler:
    spec = EngineSpec(
        id="spandrel_mps",
        name="Spandrel (Apple Silicon MPS)",
        description="HAT/SwinIR/DAT/ESRGAN系の .pth/.safetensors を spandrel で読み込み、MPS で推論します。",
        setup_hint="models/spandrel に重みを置くか UPSCALAR_SPANDREL_MODEL で指定してください。要 pip install spandrel torch torchvision。",
    )

    def is_available(self) -> bool:
        if not self._deps_ready():
            return False
        return settings.spandrel_model_path() is not None

    def availability_message(self) -> str:
        if not self._deps_ready():
            return "未導入: pip install spandrel torch torchvision"
        model = settings.spandrel_model_path()
        if model is None:
            return f"モデル未配置: {settings.SPANDREL_MODEL_DIR}/*.pth"
        return f"available: {model.name} (device={self._device_name()})"

    def upscale(self, request: UpscaleRequest) -> UpscaleResult:
        if not self._deps_ready():
            raise RuntimeError(self.availability_message())

        import torch
        from PIL import Image
        from spandrel import ImageModelDescriptor, ModelLoader

        token = request.cancel_token
        if token is not None:
            token.raise_if_cancelled()

        model_name = str(request.options.get("spandrel_model", ""))
        model_path = settings.spandrel_model_path(model_name)
        if model_path is None:
            raise RuntimeError(self.availability_message())

        device = self._device()
        descriptor = ModelLoader(device=device).load_from_file(str(model_path))
        if not isinstance(descriptor, ImageModelDescriptor):
            raise RuntimeError(f"{model_path.name} は画像アップスケールモデルではありません。")

        descriptor.to(device)
        descriptor.model.eval()
        # spandrel が対応を申告した場合のみ半精度にする(対応外モデルでの劣化/例外を避ける)。
        use_half = bool(request.half) and device.type == "mps" and descriptor.supports_half
        if use_half:
            try:
                descriptor.to(torch.half)
            except Exception:
                use_half = False
                descriptor.to(torch.float32)

        native_scale = int(descriptor.scale)
        notes = [f"spandrel model={model_path.name} arch={descriptor.architecture.name} scale=x{native_scale} device={device.type} half={use_half}"]

        with Image.open(request.input_path) as image:
            rgb = image.convert("RGB")
            input_tensor = self._to_tensor(rgb, torch, device, use_half)

        if token is not None:
            token.raise_if_cancelled()

        with torch.no_grad():
            # 生モデルではなく descriptor を呼ぶ。HAT/SwinIR/DAT 等が必要とする
            # サイズ要件パディングと出力クランプ・パディング除去を spandrel に任せる。
            output_tensor = self._infer(
                descriptor,
                input_tensor,
                native_scale,
                int(request.tile),
                torch,
                token,
            )

        result_image = self._to_image(output_tensor, torch, Image)

        target_scale = max(1, int(request.scale))
        if target_scale != native_scale:
            with Image.open(request.input_path) as image:
                base_w, base_h = image.size
            target_size = (base_w * target_scale, base_h * target_scale)
            if result_image.size != target_size:
                result_image = result_image.resize(target_size, Image.Resampling.LANCZOS)
                notes.append(f"requested x{target_scale} に Lanczos で調整")

        output_path = output_path_for(request, f"spandrel_x{target_scale}", ".png")
        result_image.save(output_path)
        return UpscaleResult(output_path=output_path, log="\n".join(notes + [f"Saved {output_path}"]))

    @staticmethod
    def _deps_ready() -> bool:
        try:
            import spandrel  # noqa: F401
            import torch  # noqa: F401
        except Exception:
            return False
        return True

    @staticmethod
    def _device():
        import torch

        if torch.backends.mps.is_available():
            return torch.device("mps")
        return torch.device("cpu")

    @classmethod
    def _device_name(cls) -> str:
        return cls._device().type

    @staticmethod
    def _to_tensor(image, torch, device, use_half):
        import numpy as np

        array = np.asarray(image, dtype=np.float32) / 255.0
        tensor = torch.from_numpy(array).permute(2, 0, 1).unsqueeze(0)
        tensor = tensor.to(device)
        return tensor.half() if use_half else tensor

    @staticmethod
    def _to_image(tensor, torch, Image):
        import numpy as np

        tensor = tensor.detach().float().clamp(0.0, 1.0).squeeze(0).permute(1, 2, 0).cpu()
        array = (tensor.numpy() * 255.0).round().astype(np.uint8)
        return Image.fromarray(array)

    @staticmethod
    def _infer(descriptor, tensor, scale, tile, torch, token):
        _, _, height, width = tensor.shape
        if tile <= 0 or (tile >= width and tile >= height):
            return descriptor(tensor)

        overlap = 16
        output = torch.zeros(
            (tensor.shape[0], tensor.shape[1], height * scale, width * scale),
            dtype=tensor.dtype,
            device=tensor.device,
        )
        for y in range(0, height, tile):
            for x in range(0, width, tile):
                if token is not None:
                    token.raise_if_cancelled()
                x0 = max(0, x - overlap)
                y0 = max(0, y - overlap)
                x1 = min(width, x + tile + overlap)
                y1 = min(height, y + tile + overlap)
                patch = tensor[:, :, y0:y1, x0:x1]
                out_patch = descriptor(patch)

                inner_x0 = (x - x0) * scale
                inner_y0 = (y - y0) * scale
                tile_w = min(tile, width - x) * scale
                tile_h = min(tile, height - y) * scale
                cropped = out_patch[
                    :,
                    :,
                    inner_y0 : inner_y0 + tile_h,
                    inner_x0 : inner_x0 + tile_w,
                ]
                output[
                    :,
                    :,
                    y * scale : y * scale + tile_h,
                    x * scale : x * scale + tile_w,
                ] = cropped
        return output
