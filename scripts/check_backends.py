import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from upscalar.app import engine_status_markdown


if __name__ == "__main__":
    print(engine_status_markdown())
