from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


SUPPORTED_IMAGE_EXTENSIONS = {
    ".bmp",
    ".jpeg",
    ".jpg",
    ".png",
    ".tif",
    ".tiff",
    ".webp",
}


def is_image_path(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS


def collect_image_paths(paths: Iterable[Path], recursive: bool = False) -> List[Path]:
    collected: List[Path] = []
    for path in paths:
        if path.is_dir():
            iterator = path.rglob("*") if recursive else path.glob("*")
            collected.extend(candidate for candidate in iterator if is_image_path(candidate))
        elif is_image_path(path):
            collected.append(path)
    return sorted(dict.fromkeys(collected))


def image_dimensions(path: Optional[Path]) -> Tuple[Optional[int], Optional[int]]:
    if path is None or not path.exists():
        return None, None
    try:
        from PIL import Image

        with Image.open(path) as image:
            return image.width, image.height
    except Exception:
        return None, None


def create_comparison_image(input_path: Path, output_path: Path, max_height: int = 720) -> Optional[Path]:
    try:
        from PIL import Image, ImageDraw

        with Image.open(input_path) as before, Image.open(output_path) as after:
            before_rgb = before.convert("RGB")
            after_rgb = after.convert("RGB")
            target_height = max(1, min(max(before_rgb.height, after_rgb.height), max_height))
            before_view = _resize_to_height(before_rgb, target_height)
            after_view = _resize_to_height(after_rgb, target_height)

            label_height = 32
            gap = 16
            margin = 16
            width = before_view.width + after_view.width + gap + margin * 2
            height = target_height + label_height + margin * 2
            canvas = Image.new("RGB", (width, height), (246, 247, 249))
            draw = ImageDraw.Draw(canvas)
            draw.text((margin, margin), "Input", fill=(34, 39, 46))
            draw.text((margin + before_view.width + gap, margin), "Output", fill=(34, 39, 46))
            y = margin + label_height
            canvas.paste(before_view, (margin, y))
            canvas.paste(after_view, (margin + before_view.width + gap, y))

            comparison_path = output_path.with_name(f"{output_path.stem}.compare.png")
            canvas.save(comparison_path)
            return comparison_path
    except Exception:
        return None


def _resize_to_height(image, height: int):
    width = max(1, round(image.width * (height / image.height)))
    return image.resize((width, height))


def write_manifest(output_path: Path, record, options: Dict[str, object]) -> Path:
    manifest_path = output_path.with_suffix(output_path.suffix + ".json")
    data = {
        "record": asdict(record),
        "options": options,
    }
    manifest_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest_path
