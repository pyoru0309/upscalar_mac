from __future__ import annotations

import sys
from pathlib import Path


SHIM = '''\
# Compatibility for torchvision>=0.17, where functional_tensor was removed.
import sys
import types

try:
    from torchvision.transforms import functional as torchvision_functional

    functional_tensor = types.ModuleType("torchvision.transforms.functional_tensor")
    functional_tensor.rgb_to_grayscale = torchvision_functional.rgb_to_grayscale
    sys.modules.setdefault("torchvision.transforms.functional_tensor", functional_tensor)
except Exception:
    pass

'''


def main() -> int:
    repo = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else Path("external/A-ESRGAN")
    target = repo / "inference_aesrgan.py"
    if not target.exists():
        raise SystemExit(f"A-ESRGAN inference script was not found: {target}")

    source = target.read_text(encoding="utf-8")
    if 'sys.modules.setdefault("torchvision.transforms.functional_tensor"' in source:
        print("A-ESRGAN torchvision compatibility patch is already present.")
        return 0

    target.write_text(SHIM + source, encoding="utf-8")
    print("Applied A-ESRGAN torchvision compatibility patch.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
