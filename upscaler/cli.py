from __future__ import annotations

import argparse
from pathlib import Path

from upscaler.history import latest_records, records_markdown
from upscaler.images import collect_image_paths
from upscaler.jobs import run_many
from upscaler.reports import write_batch_report
from upscaler.registry import build_registry


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run an Upscaler backend without the GUI.")
    parser.add_argument("--input", nargs="+", help="Input image file, directory, or list of paths.")
    parser.add_argument("--recursive", action="store_true", help="Search directories recursively.")
    parser.add_argument("--output-dir", default="", help="Output directory. Defaults to outputs/.")
    parser.add_argument("--engine", default="pillow_lanczos", choices=sorted(build_registry().keys()))
    parser.add_argument("--list-engines", action="store_true")
    parser.add_argument("--history", action="store_true", help="Print recent job history and exit.")
    parser.add_argument("--scale", type=int, default=4)
    parser.add_argument("--tile", type=int, default=0)
    parser.add_argument("--seed", type=int, default=1234)
    parser.add_argument("--no-half", action="store_true")
    parser.add_argument("--realesrgan-model", default="realesrgan-x4plus")
    parser.add_argument("--aesrgan-model", default="multi", choices=["multi", "single", "custom"])
    parser.add_argument("--spandrel-model", default="", help="models/spandrel 内のファイル名、または重みへのパス。")
    parser.add_argument("--prompt", default="")
    parser.add_argument("--negative-prompt", default="")
    parser.add_argument("--custom-command", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.list_engines:
        for engine_id, engine in build_registry().items():
            print(f"{engine_id}\t{engine.spec.name}\t{engine.availability_message()}")
        return 0
    if args.history:
        print(records_markdown(latest_records(limit=20)))
        return 0
    if not args.input:
        print("--input is required unless --list-engines or --history is used.")
        return 2

    options = {
        "scale": args.scale,
        "tile": args.tile,
        "half": not args.no_half,
        "seed": args.seed,
        "realesrgan_model": args.realesrgan_model,
        "aesrgan_model": args.aesrgan_model,
        "spandrel_model": args.spandrel_model,
        "prompt": args.prompt,
        "negative_prompt": args.negative_prompt,
        "custom_command": args.custom_command,
    }
    if args.output_dir:
        options["output_dir"] = args.output_dir

    inputs = collect_image_paths([Path(path) for path in args.input], recursive=args.recursive)
    if not inputs:
        print("No supported image files were found.")
        return 2

    records = run_many(inputs, args.engine, options)
    report_path = write_batch_report(records, options)
    for record in records:
        target = record.output_path or "-"
        print(f"{record.status}\t{record.input_path}\t{target}")
        if record.status != "ok":
            print(record.message)
    print(f"report\t{report_path}")
    return 0 if all(record.status == "ok" for record in records) else 1


if __name__ == "__main__":
    raise SystemExit(main())
