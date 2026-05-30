from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Optional, Protocol

if TYPE_CHECKING:
    from upscalar.cancellation import CancelToken


@dataclass(frozen=True)
class EngineSpec:
    id: str
    name: str
    description: str
    setup_hint: str
    non_commercial_only: bool = False


@dataclass
class UpscaleRequest:
    input_path: Path
    output_dir: Path
    scale: int = 4
    tile: int = 0
    half: bool = True
    seed: int = 1234
    prompt: str = ""
    negative_prompt: str = ""
    custom_command: str = ""
    options: Dict[str, object] = field(default_factory=dict)
    cancel_token: Optional["CancelToken"] = None


@dataclass
class UpscaleResult:
    output_path: Path
    log: str


class Upscaler(Protocol):
    spec: EngineSpec

    def is_available(self) -> bool:
        ...

    def availability_message(self) -> str:
        ...

    def upscale(self, request: UpscaleRequest) -> UpscaleResult:
        ...


def output_path_for(request: UpscaleRequest, suffix: str, extension: Optional[str] = None) -> Path:
    request.output_dir.mkdir(parents=True, exist_ok=True)
    source = request.input_path
    ext = extension or source.suffix or ".png"
    if not ext.startswith("."):
        ext = f".{ext}"
    job_id = str(request.options.get("job_id", "")).strip()
    job_suffix = f"_{job_id}" if job_id else ""
    return request.output_dir / f"{source.stem}_{suffix}{job_suffix}{ext}"
