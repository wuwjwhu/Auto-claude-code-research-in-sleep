"""Unit tests for the paper-illustration-cpa-image2 helper."""

from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parent.parent
HELPER_PATH = ROOT / "skills" / "paper-illustration-cpa-image2" / "paper_illustration_cpa_image2.py"
SPEC = importlib.util.spec_from_file_location("paper_illustration_cpa_image2", HELPER_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

PNG_BYTES = MODULE.PNG_SIGNATURE + b"fake-png-payload"


class PaperIllustrationCpaImage2Tests(unittest.TestCase):
    def test_cpa_wrapper_path_uses_bundled_skill_wrapper(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            wrapper = MODULE.cpa_wrapper_path(Path(tmpdir))
        self.assertEqual(wrapper, (ROOT / "skills" / "paper-illustration-cpa-image2" / "cpa_image_api.py").resolve())

    def test_preflight_succeeds_with_environment_and_wrapper(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            json_out = Path(tmpdir) / "preflight.json"
            with mock.patch.dict(
                os.environ,
                {"CPA_API_BASE": "http://127.0.0.1:8080", "CPA_API_KEY": "test-key"},
            ):
                exit_code = MODULE.run_preflight(Path(tmpdir), json_out=json_out)
            payload = json.loads(json_out.read_text(encoding="utf-8"))
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["ok"])
        self.assertTrue(payload["importOk"])

    def test_render_uses_wrapper_and_copies_valid_png(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            source_png = workspace / "source.png"
            source_png.write_bytes(PNG_BYTES)

            class Generated:
                saved_path = str(source_png)
                revised_prompt = "revised"

            fake_module = mock.Mock()
            fake_module.ImageGenConfig = mock.Mock(return_value=mock.Mock())
            fake_module.generate = mock.Mock(return_value=[Generated()])

            with mock.patch.object(MODULE, "load_cpa_module", return_value=fake_module):
                exit_code = MODULE.run_render(
                    workspace,
                    prompt="Draw a workflow.",
                    iteration=1,
                    size="1024x1024",
                    quality="low",
                    model="gpt-image-2",
                    timeout=5,
                )
            target = workspace / "figures" / "ai_generated" / "figure_v1.png"
            receipt = workspace / "figures" / "ai_generated" / "render_v1.json"
            payload = json.loads(receipt.read_text(encoding="utf-8"))
            self.assertEqual(exit_code, 0)
            self.assertEqual(target.read_bytes(), PNG_BYTES)
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["renderer"], "cpa-image2")
            self.assertEqual(payload["revisedPrompt"], "revised")

    def test_finalize_and_verify_emit_expected_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            image = workspace / "input.png"
            image.write_bytes(PNG_BYTES)
            finalize_code = MODULE.run_finalize(
                workspace,
                best_image=image,
                caption="Caption.",
                label="fig:test",
                score=9.0,
                review_summary="Looks good.",
            )
            verify_code = MODULE.run_verify(workspace)
            figures_dir = workspace / "figures" / "ai_generated"
            review_log = json.loads((figures_dir / "review_log.json").read_text(encoding="utf-8"))
            self.assertEqual(finalize_code, 0)
            self.assertEqual(verify_code, 0)
            self.assertTrue((figures_dir / "figure_final.png").is_file())
            self.assertIn("figure_final.png", (figures_dir / "latex_include.tex").read_text(encoding="utf-8"))
            self.assertEqual(review_log["renderer"], "cpa-image2")


if __name__ == "__main__":
    unittest.main()
