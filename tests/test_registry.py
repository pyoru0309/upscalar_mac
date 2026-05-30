import unittest

from upscalar.registry import build_registry


class RegistryTest(unittest.TestCase):
    def test_expected_engines_are_registered(self):
        registry = build_registry()
        self.assertNotIn("supir", registry)
        self.assertIn("aesrgan", registry)
        self.assertIn("realesrgan_ncnn", registry)
        self.assertIn("external_command", registry)
        self.assertIn("pillow_lanczos", registry)
        self.assertIn("spandrel_mps", registry)


if __name__ == "__main__":
    unittest.main()
