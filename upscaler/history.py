from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, List, Optional

from upscaler import settings


@dataclass
class JobRecord:
    id: str
    created_at: float
    engine_id: str
    input_path: str
    output_path: Optional[str]
    scale: int
    status: str
    elapsed_seconds: float
    message: str
    input_width: Optional[int] = None
    input_height: Optional[int] = None
    output_width: Optional[int] = None
    output_height: Optional[int] = None
    manifest_path: Optional[str] = None
    comparison_path: Optional[str] = None


def new_job_id() -> str:
    return uuid.uuid4().hex[:12]


def append_record(record: JobRecord, history_path: Path | None = None) -> None:
    path = history_path or settings.HISTORY_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")


def read_records(history_path: Path | None = None) -> List[JobRecord]:
    path = history_path or settings.HISTORY_PATH
    if not path.exists():
        return []
    records: List[JobRecord] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        raw = json.loads(line)
        known = {field.name for field in JobRecord.__dataclass_fields__.values()}
        records.append(JobRecord(**{key: value for key, value in raw.items() if key in known}))
    return records


def latest_records(limit: int = 20, history_path: Path | None = None) -> List[JobRecord]:
    records = read_records(history_path)
    return list(reversed(records[-limit:]))


def records_markdown(records: Iterable[JobRecord]) -> str:
    rows = ["| Time | Engine | Status | Input | Output | Compare |", "| --- | --- | --- | --- | --- | --- |"]
    for record in records:
        created = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(record.created_at))
        input_name = Path(record.input_path).name
        output_name = Path(record.output_path).name if record.output_path else "-"
        compare_name = Path(record.comparison_path).name if record.comparison_path else "-"
        size = "-"
        if record.output_width and record.output_height:
            size = f"{record.output_width}x{record.output_height}"
        rows.append(f"| {created} | {record.engine_id} | {record.status} | {input_name} | {output_name} ({size}) | {compare_name} |")
    return "\n".join(rows) if len(rows) > 2 else "履歴はまだありません。"
