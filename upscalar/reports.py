from __future__ import annotations

import time
from pathlib import Path
from typing import Dict, Sequence

from upscalar import settings
from upscalar.history import JobRecord


def write_batch_report(records: Sequence[JobRecord], options: Dict[str, object]) -> Path:
    output_dir = _report_output_dir(records, options)
    output_dir.mkdir(parents=True, exist_ok=True)
    batch_id = str(options.get("batch_id", "batch")).strip() or "batch"
    report_path = output_dir / f"batch_report_{batch_id}.md"
    ok_count = sum(1 for record in records if record.status == "ok")
    elapsed = sum(record.elapsed_seconds for record in records)

    lines = [
        "# Upscalar Batch Report",
        "",
        f"- Created: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"- Batch ID: `{batch_id}`",
        f"- Engine: `{records[0].engine_id if records else '-'}`",
        f"- Jobs: {len(records)}",
        f"- Succeeded: {ok_count}",
        f"- Failed: {len(records) - ok_count}",
        f"- Total elapsed: {elapsed:.2f}s",
        "",
        "## Options",
        "",
        "| Key | Value |",
        "| --- | --- |",
    ]
    for key in sorted(options):
        lines.append(f"| {key} | {options[key]} |")

    lines.extend(
        [
            "",
            "## Results",
            "",
            "| Status | Input | Output | Compare | Size | Seconds |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for record in records:
        size = "-"
        if record.input_width and record.input_height and record.output_width and record.output_height:
            size = f"{record.input_width}x{record.input_height} -> {record.output_width}x{record.output_height}"
        output = record.output_path or "-"
        compare = record.comparison_path or "-"
        lines.append(
            f"| {record.status} | {record.input_path} | {output} | {compare} | {size} | {record.elapsed_seconds:.2f} |"
        )

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_path


def _report_output_dir(records: Sequence[JobRecord], options: Dict[str, object]) -> Path:
    if options.get("output_dir"):
        return Path(str(options["output_dir"]))
    for record in records:
        if record.output_path:
            return Path(record.output_path).parent
    return settings.OUTPUTS_DIR
