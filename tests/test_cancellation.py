import tempfile
import time
import unittest
from pathlib import Path

from PIL import Image

from upscalar.cancellation import CancelToken, UpscaleCancelled
from upscalar.engines.utils import run_command
from upscalar.jobs import run_recorded


class CancellationTest(unittest.TestCase):
    def test_raise_if_cancelled(self):
        token = CancelToken()
        token.raise_if_cancelled()  # 未キャンセルなら何も起きない
        token.cancel()
        self.assertTrue(token.cancelled)
        with self.assertRaises(UpscaleCancelled):
            token.raise_if_cancelled()

    def test_run_command_cancels_running_process(self):
        token = CancelToken()
        token.cancel()
        started = time.time()
        with self.assertRaises(UpscaleCancelled):
            run_command(["sleep", "5"], cancel_token=token)
        self.assertLess(time.time() - started, 3.0)

    def test_run_recorded_records_cancelled_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.png"
            Image.new("RGB", (8, 8), "white").save(source)
            token = CancelToken()
            token.cancel()
            record = run_recorded(
                source,
                "pillow_lanczos",
                {"scale": 2, "output_dir": str(Path(tmp) / "outputs")},
                history_path=Path(tmp) / "history.jsonl",
                cancel_token=token,
            )
            self.assertEqual(record.status, "cancelled")
            self.assertIsNone(record.output_path)


if __name__ == "__main__":
    unittest.main()
