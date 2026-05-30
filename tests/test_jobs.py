import tempfile
import unittest
from pathlib import Path

from PIL import Image

from upscalar.history import JobRecord, latest_records, records_markdown
from upscalar.images import collect_image_paths
from upscalar.jobs import run_recorded, successful_outputs


class JobsTest(unittest.TestCase):
    def test_pillow_job_records_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.png"
            Image.new("RGB", (8, 8), "white").save(source)
            record = run_recorded(
                source,
                "pillow_lanczos",
                {"scale": 2, "tile": 0, "half": True, "output_dir": str(Path(tmp) / "outputs")},
                history_path=Path(tmp) / "history.jsonl",
            )
            self.assertEqual(record.status, "ok")
            self.assertTrue(record.output_path)
            self.assertTrue(Path(record.output_path).exists())
            self.assertTrue(record.manifest_path)
            self.assertTrue(Path(record.manifest_path).exists())
            self.assertTrue(record.comparison_path)
            self.assertTrue(Path(record.comparison_path).exists())
            self.assertEqual(record.input_width, 8)
            self.assertEqual(record.output_width, 16)
            self.assertEqual(successful_outputs([record]), [record.output_path])

    def test_history_markdown_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            markdown = records_markdown(latest_records(history_path=Path(tmp) / "missing.jsonl"))
            self.assertIn("履歴はまだありません", markdown)

    def test_history_markdown_record(self):
        record = JobRecord(
            id="abc",
            created_at=1.0,
            engine_id="pillow_lanczos",
            input_path="/tmp/input.png",
            output_path="/tmp/output.png",
            scale=2,
            status="ok",
            elapsed_seconds=0.1,
            message="done",
        )
        markdown = records_markdown([record])
        self.assertIn("pillow_lanczos", markdown)
        self.assertIn("output.png", markdown)

    def test_collect_image_paths_from_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            Image.new("RGB", (4, 4), "white").save(root / "a.png")
            (root / "ignored.txt").write_text("x", encoding="utf-8")
            self.assertEqual(collect_image_paths([root]), [root / "a.png"])

    def test_repeated_jobs_do_not_overwrite_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.png"
            output_dir = root / "outputs"
            Image.new("RGB", (8, 8), "white").save(source)
            options = {"scale": 2, "tile": 0, "half": True, "output_dir": str(output_dir)}
            first = run_recorded(source, "pillow_lanczos", options, history_path=root / "history.jsonl")
            second = run_recorded(source, "pillow_lanczos", options, history_path=root / "history.jsonl")
            self.assertNotEqual(first.output_path, second.output_path)
            self.assertEqual(len([path for path in output_dir.glob("*.png") if ".compare" not in path.name]), 2)
            self.assertEqual(len(list(output_dir.glob("*.compare.png"))), 2)


if __name__ == "__main__":
    unittest.main()
