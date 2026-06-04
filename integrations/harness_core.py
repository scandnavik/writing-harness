#!/usr/bin/env python3
"""Agent-agnostic core for the writing-harness reminder gates.

This module holds the *decision* logic shared by the non-Claude adapters:
  - integrations/codex/      (OpenAI Codex CLI command hooks)
  - integrations/hermes/     (NousResearch Hermes Agent plugin)

It is pure stdlib and imports nothing agent-specific. Each adapter only does
two things: translate its host's tool event into (file_path, file_text), and
surface the returned reminder string through whatever channel that host gives
it. All the "should we remind, and with what text" logic lives here, in one
place, so a rule change lands once.

The Claude Code hooks under hooks/ intentionally keep their own self-contained
copy of this config, so existing installs are untouched. If you'd rather have a
single config home for every agent, point those hooks at this module too
(they share the exact same regex and messages).

Two independent, warn-only gates:
  - harness_reminder(path, text):
        "this reader-facing Chinese long-form .md has no 3-station sign-off."
  - tier_reminder(path):
        "this is a client-facing deliverable, attach an evidence pack."
Each returns a reminder string, or None when nothing should fire.

==============================================================================
CONFIGURE THIS — same knobs as the Claude hooks. Patterns are regex, matched
against the forward-slashed path. Replace the placeholders with your own paths.
==============================================================================
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable, Iterator, Optional

# --- CONFIG: directories holding reader-facing long-form content ---
INCLUDES = [
    r"content[/\\]",          # e.g. content/ blog posts, essays
    r"posts[/\\]",            # e.g. posts/
    r"articles[/\\]",         # e.g. articles/
    # add your own: r"my-outputs[/\\]01-writing[/\\]",
]

# --- CONFIG: sub-paths to skip even if they match INCLUDES ---
EXCLUDES = [
    r"[/\\]drafts[/\\]",
    r"[/\\]_index[/\\]",
    r"[/\\]CHANGELOG\.md$",
    r"[/\\]README\.md$",
    r"[/\\]\.gitignore$",
]

# --- CONFIG: outbound / client-facing roots (L3) ---
L3_INCLUDES = [
    r"clients[/\\]",                 # e.g. clients/<name>/
    r"proposals[/\\]",               # e.g. proposals/
    r"deliverables[/\\]",            # e.g. deliverables/
    # name-specific example (replace with your real client folder names):
    # r"projects[/\\](ClientA|ClientB|ClientC)",
]

# --- CONFIG: internal sub-paths to skip even if they match L3_INCLUDES ---
L3_EXCLUDES = [
    r"[/\\](consent|intake|internal|sessions)[/\\]",
    r"[/\\]payment[/\\]",
    r"[/\\]CHANGELOG\.md$",
    r"[/\\]README\.md$",
    r"[/\\]_registry[/\\]",
    r"[/\\]raw[/\\]",
    r"[/\\]\.gitignore$",
]

# --- CONFIG: where the methodology + checker live, as quoted in the reminder.
# These are just strings shown to the agent. Point them at YOUR install path.
HARNESS_PATH = "writing-harness/methodology/writing-harness.md"
CHECKER_PATH = "writing-harness/scripts/taiwan-style-check.py"
# ==============================================================================

MARKER_RE = re.compile(r"<!--\s*writing-harness:")
SKELETON_RE = re.compile(r"^status:\s*draft-skeleton\s*$", re.MULTILINE)

# apply_patch (Codex / Hermes write tools) name the file inside the patch body:
#   *** Add File: path/to/x.md
#   *** Update File: path/to/x.md
#   *** Move to: path/to/y.md
_PATCH_PATH_RE = re.compile(
    r"^\*\*\*\s+(?:(?:Add|Update|Delete)\s+File|Move\s+to):\s*(.+?)\s*$",
    re.MULTILINE,
)
# git-style headers some tools emit: +++ b/path/to/x.md
_GIT_PATH_RE = re.compile(r"^\+\+\+\s+[ab]/(.+?)\s*$", re.MULTILINE)


def match_any(path: str, patterns: Iterable[str]) -> bool:
    return any(re.search(p, path) for p in patterns)


def iter_strings(obj) -> Iterator[str]:
    """Yield every string leaf in a nested dict/list/str structure."""
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from iter_strings(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            yield from iter_strings(v)


def extract_paths_from_text(text: str) -> list[str]:
    """Pull file paths out of an apply_patch / diff blob. Order-preserving, deduped."""
    seen: dict[str, None] = {}
    for rx in (_PATCH_PATH_RE, _GIT_PATH_RE):
        for m in rx.finditer(text or ""):
            seen.setdefault(m.group(1).strip(), None)
    return list(seen)


def collect_candidate_paths(*objects) -> list[str]:
    """Best-effort file paths from arbitrary tool input/output objects.

    Looks at common path-ish keys plus any apply_patch/diff bodies found in
    string leaves. Returns an order-preserving, deduped list.
    """
    seen: dict[str, None] = {}

    def add(p) -> None:
        if isinstance(p, str) and p.strip():
            seen.setdefault(p.strip(), None)

    for obj in objects:
        if isinstance(obj, dict):
            for key in ("file_path", "filePath", "path", "target", "filename"):
                add(obj.get(key))
        for s in iter_strings(obj):
            for p in extract_paths_from_text(s):
                add(p)
    return list(seen)


def is_markdown(path: str) -> bool:
    return Path(path).suffix.lower() == ".md"


def harness_reminder(raw_path: str, text: str) -> Optional[str]:
    """Reminder for a reader-facing Chinese long-form .md with no sign-off.

    `text` is the file's current content (the caller reads it). Returns the
    reminder string, or None if this path/file shouldn't trigger.
    """
    if not raw_path or not is_markdown(raw_path):
        return None
    norm = raw_path.replace("\\", "/")
    if not match_any(norm, INCLUDES) or match_any(norm, EXCLUDES):
        return None
    if MARKER_RE.search(text or ""):
        return None  # already signed off
    if SKELETON_RE.search(text or ""):
        return None  # draft-skeleton is explicitly exempt
    return (
        "[寫作 Harness 提醒] 偵測到寫作路徑中文長文且尚無三站留證："
        f"{raw_path}\n"
        f"宣告完成前須穿過 {HARNESS_PATH}："
        "S0 輸入閘（要真實素材而無 → STOP 跟需求方要，禁編造）→ "
        f"S1 機械閘（{CHECKER_PATH} exit 0）→ "
        "S2 判斷閘（結構/聲音 5 問＋敘事姿態＋台灣語感＋9 類語病，自審留證貼回覆）。"
        "三站過後於檔尾寫一行 `<!-- writing-harness: S0/S1/S2 ok YYYY-MM-DD -->`。"
        "（骨架請設 frontmatter `status: draft-skeleton` 即自動豁免。）"
    )


def tier_reminder(raw_path: str) -> Optional[str]:
    """Reminder that a client-facing (L3) deliverable needs an evidence pack."""
    if not raw_path:
        return None
    if match_any(raw_path, L3_INCLUDES) and not match_any(raw_path, L3_EXCLUDES):
        return (
            "[L3 對外產出偵測] 此檔將給客戶/外部看。請附 evidence pack："
            "(1) 同題重跑穩定度 (2) 引用可查 (3) 抽查覆核率 (4) 人類覆核點。"
            "無法立即附請在文件頂部標 `TODO: evidence`。"
        )
    return None


def reminders_for_paths(paths: Iterable[str]) -> list[str]:
    """Run both gates over a set of paths; read each file once. Deduped, ordered."""
    out: dict[str, None] = {}
    for raw in paths:
        if not is_markdown(raw):
            # tier gate still applies to non-.md deliverables
            t = tier_reminder(raw)
            if t:
                out.setdefault(t, None)
            continue
        try:
            text = Path(raw).read_text(encoding="utf-8")
        except Exception:
            text = ""
        for msg in (harness_reminder(raw, text), tier_reminder(raw)):
            if msg:
                out.setdefault(msg, None)
    return list(out)
