from __future__ import annotations

import json
import platform
import shutil
import stat
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INSTALL_DIR = ROOT / "external" / "realesrgan-ncnn-vulkan"
API_URL = "https://api.github.com/repos/xinntao/Real-ESRGAN/releases/tags/v0.2.5.0"


def main() -> int:
    INSTALL_DIR.mkdir(parents=True, exist_ok=True)
    release = fetch_json(API_URL)
    asset = select_asset(release.get("assets", []))
    archive_path = download(asset["browser_download_url"], asset["name"])
    extract_archive(archive_path, INSTALL_DIR)
    executable = find_executable(INSTALL_DIR)
    if executable is None:
        raise SystemExit("realesrgan-ncnn-vulkan executable was not found after extraction.")
    executable.chmod(executable.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    print("Real-ESRGAN ncnn-vulkan is ready.")
    print(f'export UPSCALER_REALESRGAN_BIN="{executable}"')
    return 0


def fetch_json(url: str) -> dict:
    request = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read().decode("utf-8"))


def select_asset(assets: list[dict]) -> dict:
    system = platform.system().lower()
    machine = platform.machine().lower()
    candidates = []
    for asset in assets:
        name = asset.get("name", "").lower()
        if "ncnn-vulkan" not in name:
            continue
        if system == "darwin" and ("macos" in name or "mac" in name):
            candidates.append(asset)
        elif system == "linux" and ("linux" in name or "ubuntu" in name):
            candidates.append(asset)
        elif system == "windows" and ("windows" in name or "win" in name):
            candidates.append(asset)
    if machine in {"arm64", "aarch64"}:
        arm = [asset for asset in candidates if "arm" in asset.get("name", "").lower() or "macos" in asset.get("name", "").lower()]
        if arm:
            return arm[0]
    if candidates:
        return candidates[0]
    available = ", ".join(asset.get("name", "") for asset in assets)
    raise SystemExit(f"No suitable release asset was found. Available assets: {available}")


def download(url: str, name: str) -> Path:
    tmp_dir = Path(tempfile.mkdtemp(prefix="upscaler_realesrgan_"))
    archive_path = tmp_dir / name
    with urllib.request.urlopen(url) as response, archive_path.open("wb") as fh:
        shutil.copyfileobj(response, fh)
    return archive_path


def extract_archive(archive_path: Path, target_dir: Path) -> None:
    if archive_path.suffix == ".zip":
        with zipfile.ZipFile(archive_path) as archive:
            for member in archive.infolist():
                member_path = (target_dir / member.filename).resolve()
                if not str(member_path).startswith(str(target_dir.resolve())):
                    raise SystemExit(f"Unsafe archive member: {member.filename}")
            archive.extractall(target_dir)
        return
    if archive_path.suffixes[-2:] == [".tar", ".gz"] or archive_path.suffix in {".tgz", ".gz"}:
        with tarfile.open(archive_path) as archive:
            for member in archive.getmembers():
                member_path = (target_dir / member.name).resolve()
                if not str(member_path).startswith(str(target_dir.resolve())):
                    raise SystemExit(f"Unsafe archive member: {member.name}")
            archive.extractall(target_dir)
        return
    raise SystemExit(f"Unsupported archive type: {archive_path.name}")


def find_executable(root: Path) -> Path | None:
    names = ["realesrgan-ncnn-vulkan", "realesrgan-ncnn-vulkan.exe"]
    for path in root.rglob("*"):
        if path.name in names and path.is_file():
            return path
    return None


if __name__ == "__main__":
    raise SystemExit(main())
