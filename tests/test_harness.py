#!/usr/bin/env python3
"""Smoke tests for the writing-harness checkers. Pure stdlib, no pytest needed.

Run:
    python tests/test_harness.py
Exit 0 = all pass, 1 = a test failed.
"""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STYLE = ROOT / "scripts" / "taiwan-style-check.py"
VERBOSITY = ROOT / "scripts" / "verbosity-check.py"
BLOATED = ROOT / "examples" / "bloated-sample.md"
CLEAN = ROOT / "examples" / "clean-sample.md"
PY = sys.executable


def run(script, *args):
    return subprocess.run(
        [PY, str(script), *map(str, args)],
        capture_output=True, text=True, encoding="utf-8",
    )


def write_tmp(text):
    fd = tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8")
    fd.write(text)
    fd.close()
    return Path(fd.name)


class TaiwanStyleCheck(unittest.TestCase):
    def test_clean_passes(self):
        p = write_tmp("這是一段乾淨的繁體中文，沒有違規。\n收尾就停。\n")
        try:
            r = run(STYLE, p)
            self.assertEqual(r.returncode, 0, r.stdout)
        finally:
            p.unlink(missing_ok=True)

    def test_em_dash_fails(self):
        p = write_tmp("這裡用了破折號——這就違規了。\n")
        try:
            r = run(STYLE, p)
            self.assertEqual(r.returncode, 10, r.stdout)
        finally:
            p.unlink(missing_ok=True)

    def test_halfwidth_punct_fails(self):
        p = write_tmp("中文句子裡夾了半形逗號,這樣不行。\n")
        try:
            r = run(STYLE, p)
            self.assertEqual(r.returncode, 10, r.stdout)
        finally:
            p.unlink(missing_ok=True)

    def test_mainland_word_fails(self):
        p = write_tmp("我們要處理這些數據和信息。\n")
        try:
            r = run(STYLE, p)
            self.assertEqual(r.returncode, 10, r.stdout)
        finally:
            p.unlink(missing_ok=True)

    def test_noise_frame_fails(self):
        p = write_tmp("其實這件事很簡單。\n")
        try:
            r = run(STYLE, p)
            self.assertEqual(r.returncode, 10, r.stdout)
        finally:
            p.unlink(missing_ok=True)


class VerbosityCheck(unittest.TestCase):
    def test_bloated_has_findings(self):
        r = run(VERBOSITY, BLOATED, "--format=json")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)

    def test_clean_has_no_findings(self):
        r = run(VERBOSITY, CLEAN, "--format=json")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
