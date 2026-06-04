#!/usr/bin/env python3
"""Tests for the multi-agent integrations (Codex hooks + Hermes plugin + core).

Pure stdlib, no pytest. Run:
    python tests/test_integrations.py
"""
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INTEGRATIONS = ROOT / "integrations"
CODEX_HARNESS = INTEGRATIONS / "codex" / "writing-harness-gate.py"
CODEX_TIER = INTEGRATIONS / "codex" / "output-tier-gate.py"
HERMES_PLUGIN = INTEGRATIONS / "hermes" / "writing_harness_plugin.py"
PY = sys.executable

sys.path.insert(0, str(INTEGRATIONS))
import harness_core as core  # noqa: E402


def md_under(dirname, text="這是一段需要過三站的中文長文，先放著。\n"):
    """Create a real .md file under a temp dir whose path contains `dirname`."""
    base = Path(tempfile.mkdtemp()) / dirname
    base.mkdir(parents=True, exist_ok=True)
    f = base / "post.md"
    f.write_text(text, encoding="utf-8")
    return f


class CoreLogic(unittest.TestCase):
    def test_extract_apply_patch_paths(self):
        patch = (
            "*** Begin Patch\n"
            "*** Add File: content/new-post.md\n"
            "+hello\n"
            "*** Update File: articles/old.md\n"
            "*** Move to: posts/moved.md\n"
            "*** End Patch\n"
        )
        paths = core.extract_paths_from_text(patch)
        self.assertEqual(
            paths, ["content/new-post.md", "articles/old.md", "posts/moved.md"]
        )

    def test_collect_from_codex_tool_input(self):
        tool_input = {"input": "*** Update File: content/a.md\n@@\n-x\n+y\n"}
        self.assertIn("content/a.md", core.collect_candidate_paths(tool_input))

    def test_collect_from_direct_path_key(self):
        self.assertIn("content/b.md", core.collect_candidate_paths({"file_path": "content/b.md"}))

    def test_harness_reminder_fires_on_included(self):
        self.assertIsNotNone(core.harness_reminder("content/x.md", "純內文，沒有留證標記"))

    def test_harness_reminder_skips_excluded(self):
        self.assertIsNone(core.harness_reminder("content/drafts/x.md", "內文"))

    def test_harness_reminder_skips_signed_off(self):
        self.assertIsNone(
            core.harness_reminder("content/x.md", "內文\n<!-- writing-harness: S0/S1/S2 ok 2026-06-04 -->\n")
        )

    def test_harness_reminder_skips_skeleton(self):
        self.assertIsNone(core.harness_reminder("content/x.md", "status: draft-skeleton\n內文"))

    def test_harness_reminder_skips_non_md(self):
        self.assertIsNone(core.harness_reminder("content/x.txt", "內文"))

    def test_tier_reminder_fires_on_client_path(self):
        self.assertIsNotNone(core.tier_reminder("clients/acme/proposal.md"))

    def test_tier_reminder_skips_internal_subpath(self):
        self.assertIsNone(core.tier_reminder("clients/acme/intake/notes.md"))


class CodexAdapter(unittest.TestCase):
    def _run(self, script, payload):
        return subprocess.run(
            [PY, str(script)],
            input=json.dumps(payload),
            capture_output=True, text=True, encoding="utf-8",
        )

    def test_codex_harness_emits_system_message(self):
        f = md_under("content")
        payload = {
            "hook_event_name": "PostToolUse",
            "tool_name": "apply_patch",
            "tool_input": {"input": f"*** Update File: {f}\n@@\n+x\n"},
            "tool_response": {},
        }
        r = self._run(CODEX_HARNESS, payload)
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout)
        self.assertIn("systemMessage", out)
        self.assertIn("寫作 Harness", out["systemMessage"])

    def test_codex_harness_silent_when_signed_off(self):
        f = md_under("content", "內文\n<!-- writing-harness: S0/S1/S2 ok 2026-06-04 -->\n")
        payload = {
            "hook_event_name": "PostToolUse",
            "tool_input": {"input": f"*** Update File: {f}\n"},
        }
        r = self._run(CODEX_HARNESS, payload)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), "")

    def test_codex_tier_emits_on_client_path(self):
        f = md_under("clients")
        payload = {
            "hook_event_name": "PostToolUse",
            "tool_input": {"input": f"*** Add File: {f}\n+x\n"},
        }
        r = self._run(CODEX_TIER, payload)
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout)
        self.assertIn("L3", out["systemMessage"])


class HermesPlugin(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location("writing_harness_plugin", HERMES_PLUGIN)
        self.plugin = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.plugin)
        self.plugin._pending.clear()

    def test_register_wires_both_hooks(self):
        registered = {}

        class Ctx:
            def register_hook(self, name, fn):
                registered[name] = fn

        self.plugin.register(Ctx())
        self.assertIn("post_tool_call", registered)
        self.assertIn("pre_llm_call", registered)

    def test_observe_then_inject(self):
        f = md_under("content")
        # post_tool_call observes the write (Hermes calls hooks by keyword)
        self.plugin._on_post_tool(
            tool_name="write_file",
            args={"path": str(f)},
            result=f"wrote {f}",
            task_id="t1",
            duration_ms=3,
        )
        injected = self.plugin._inject_pending(messages=[])
        self.assertIsNotNone(injected)
        self.assertIn("writing-harness", injected["context"])
        # queue drained — next turn injects nothing
        self.assertIsNone(self.plugin._inject_pending())


if __name__ == "__main__":
    unittest.main(verbosity=2)
