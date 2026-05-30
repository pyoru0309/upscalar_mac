from __future__ import annotations

import shlex
import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Iterable, Optional, Sequence

if TYPE_CHECKING:
    from upscalar.cancellation import CancelToken


def resolve_executable(command: str) -> Optional[str]:
    candidate = Path(command).expanduser()
    if candidate.exists():
        return str(candidate)
    return shutil.which(command)


def run_command(
    args: Sequence[str],
    cwd: Optional[Path] = None,
    cancel_token: Optional["CancelToken"] = None,
) -> str:
    from upscalar.cancellation import UpscaleCancelled

    printable = shlex.join([str(arg) for arg in args])
    proc = subprocess.Popen(
        [str(arg) for arg in args],
        cwd=str(cwd) if cwd else None,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    while True:
        try:
            stdout, stderr = proc.communicate(timeout=0.25)
            break
        except subprocess.TimeoutExpired:
            if cancel_token is not None and cancel_token.cancelled:
                proc.terminate()
                try:
                    proc.communicate(timeout=2.0)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.communicate()
                raise UpscaleCancelled(f"キャンセルされました。\n$ {printable}")

    log = "\n".join(
        part
        for part in (
            f"$ {printable}",
            (stdout or "").strip(),
            (stderr or "").strip(),
        )
        if part
    )
    if proc.returncode != 0:
        raise RuntimeError(log)
    return log


def first_existing(paths: Iterable[Path]) -> Optional[Path]:
    for path in paths:
        if path.exists():
            return path
    return None
