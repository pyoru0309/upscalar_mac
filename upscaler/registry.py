from __future__ import annotations

from typing import Dict, List

from upscaler.engines import (
    AESRGANUpscaler,
    ExternalCommandUpscaler,
    PillowLanczosUpscaler,
    RealESRGANNcnnUpscaler,
    SpandrelMPSUpscaler,
)
from upscaler.engines.base import Upscaler


def build_registry() -> Dict[str, Upscaler]:
    engines: List[Upscaler] = [
        AESRGANUpscaler(),
        SpandrelMPSUpscaler(),
        RealESRGANNcnnUpscaler(),
        ExternalCommandUpscaler(),
        PillowLanczosUpscaler(),
    ]
    return {engine.spec.id: engine for engine in engines}
