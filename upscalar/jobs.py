from __future__ import annotations

import time
import traceback
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Sequence

from upscalar import settings
from upscalar.cancellation import CancelToken, UpscaleCancelled
from upscalar.engines.base import UpscaleRequest, UpscaleResult
from upscalar.history import JobRecord, append_record, new_job_id
from upscalar.images import create_comparison_image, image_dimensions, write_manifest
from upscalar.registry import build_registry


def build_request(
    input_path: Path,
    engine_options: Dict[str, object],
    output_dir: Path | None = None,
    cancel_token: CancelToken | None = None,
) -> UpscaleRequest:
    resolved_input = input_path.expanduser().resolve()
    requested_output_dir = engine_options.get("output_dir")
    target_output_dir = output_dir or (Path(str(requested_output_dir)) if requested_output_dir else settings.OUTPUTS_DIR)
    target_output_dir = target_output_dir.expanduser().resolve()
    return UpscaleRequest(
        input_path=resolved_input,
        output_dir=target_output_dir,
        scale=int(engine_options.get("scale", 4)),
        tile=int(engine_options.get("tile", 0)),
        half=bool(engine_options.get("half", True)),
        seed=int(engine_options.get("seed", 1234)),
        prompt=str(engine_options.get("prompt", "")),
        negative_prompt=str(engine_options.get("negative_prompt", "")),
        custom_command=str(engine_options.get("custom_command", "")),
        options=dict(engine_options),
        cancel_token=cancel_token,
    )


def run_one(
    input_path: Path,
    engine_id: str,
    engine_options: Dict[str, object],
    cancel_token: CancelToken | None = None,
) -> UpscaleResult:
    settings.ensure_workspace_dirs()
    registry = build_registry()
    if engine_id not in registry:
        raise ValueError(f"Unknown engine: {engine_id}")
    engine = registry[engine_id]
    if not engine.is_available():
        raise RuntimeError(f"{engine.spec.name} is not available: {engine.availability_message()}\n{engine.spec.setup_hint}")
    if cancel_token is not None:
        cancel_token.raise_if_cancelled()
    request = build_request(input_path=input_path, engine_options=engine_options, cancel_token=cancel_token)
    return engine.upscale(request)


def run_many_iter(
    input_paths: Sequence[Path],
    engine_id: str,
    engine_options: Dict[str, object],
    history_path: Path | None = None,
    cancel_token: CancelToken | None = None,
) -> Iterator[tuple[int, int, JobRecord]]:
    batch_options = dict(engine_options)
    batch_id = str(batch_options.setdefault("batch_id", new_job_id()))
    engine_options["batch_id"] = batch_id
    total = len(input_paths)
    for index, input_path in enumerate(input_paths, start=1):
        if cancel_token is not None and cancel_token.cancelled:
            return
        record = run_recorded(
            input_path=input_path,
            engine_id=engine_id,
            engine_options=batch_options,
            history_path=history_path,
            cancel_token=cancel_token,
        )
        yield index, total, record


def run_many(
    input_paths: Sequence[Path],
    engine_id: str,
    engine_options: Dict[str, object],
    history_path: Path | None = None,
    cancel_token: CancelToken | None = None,
) -> List[JobRecord]:
    return [
        record
        for _, _, record in run_many_iter(
            input_paths,
            engine_id,
            engine_options,
            history_path=history_path,
            cancel_token=cancel_token,
        )
    ]


def run_recorded(
    input_path: Path,
    engine_id: str,
    engine_options: Dict[str, object],
    history_path: Path | None = None,
    cancel_token: CancelToken | None = None,
) -> JobRecord:
    started = time.time()
    job_id = new_job_id()
    run_options = dict(engine_options)
    run_options["job_id"] = job_id
    try:
        input_width, input_height = image_dimensions(input_path)
        result = run_one(
            input_path=input_path,
            engine_id=engine_id,
            engine_options=run_options,
            cancel_token=cancel_token,
        )
        output_path = Path(result.output_path)
        output_width, output_height = image_dimensions(output_path)
        comparison_path = create_comparison_image(input_path, output_path)
        record = JobRecord(
            id=job_id,
            created_at=started,
            engine_id=engine_id,
            input_path=str(input_path),
            output_path=str(output_path),
            scale=int(engine_options.get("scale", 4)),
            status="ok",
            elapsed_seconds=time.time() - started,
            message=result.log,
            input_width=input_width,
            input_height=input_height,
            output_width=output_width,
            output_height=output_height,
            comparison_path=str(comparison_path) if comparison_path else None,
        )
        record.manifest_path = str(output_path.with_suffix(output_path.suffix + ".json"))
        write_manifest(output_path, record, run_options)
    except UpscaleCancelled:
        input_width, input_height = image_dimensions(input_path)
        record = JobRecord(
            id=job_id,
            created_at=started,
            engine_id=engine_id,
            input_path=str(input_path),
            output_path=None,
            scale=int(engine_options.get("scale", 4)),
            status="cancelled",
            elapsed_seconds=time.time() - started,
            message="キャンセルされました。",
            input_width=input_width,
            input_height=input_height,
        )
    except Exception as exc:
        input_width, input_height = image_dimensions(input_path)
        record = JobRecord(
            id=job_id,
            created_at=started,
            engine_id=engine_id,
            input_path=str(input_path),
            output_path=None,
            scale=int(engine_options.get("scale", 4)),
            status="error",
            elapsed_seconds=time.time() - started,
            message=f"{exc}\n\n{traceback.format_exc(limit=6)}",
            input_width=input_width,
            input_height=input_height,
        )
    append_record(record, history_path=history_path)
    return record


def successful_outputs(records: Iterable[JobRecord]) -> List[str]:
    return [record.output_path for record in records if record.status == "ok" and record.output_path]


def successful_comparisons(records: Iterable[JobRecord]) -> List[str]:
    return [record.comparison_path for record in records if record.status == "ok" and record.comparison_path]
