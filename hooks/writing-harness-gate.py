#!/usr/bin/env python3
"""Writing-harness gate (PostToolUse, warn-only — does not block).

Hook for Claude Code (or any agent harness that fires PostToolUse on file
writes). When a reader-facing Chinese long-form .md is written and it has no
harness sign-off marker (and isn't a mechanical skeleton), it injects a
reminder: before claiming done, pass the 3 stations of writing-harness.md, and
write a sign-off line at the file tail:
    <!-- writing-harness: S0/S1/S2 ok YYYY-MM-DD -->

Warn-only by design. Observe false-positive rate first; once clean, you can
promote it to a hard Stop hook.

==============================================================================
CONFIGURE THIS — point INCLUDES at the directories where your reader-facing
long-form content lives, and EXCLUDES at sub-paths to skip (indexes, drafts,
machine-generated). Patterns are regex matched against the forward-slashed
path. Examples below; replace with your own.
==============================================================================
"""
import json
import re
import sys
from pathlib import Path

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

# Path to the harness checker, as referenced in the reminder text.
HARNESS_PATH = "~/.claude/skills/writing-harness/methodology/writing-harness.md"
CHECKER_PATH = "~/.claude/skills/writing-harness/scripts/taiwan-style-check.py"
# ==============================================================================

MARKER_RE = re.compile(r"<!--\s*writing-harness:")
SKELETON_RE = re.compile(r"^status:\s*draft-skeleton\s*$", re.MULTILINE)


def match_any(path: str, patterns) -> bool:
    return any(re.search(p, path) for p in patterns)


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return

    if data.get("tool_name", "") not in {"Edit", "Write", "MultiEdit"}:
        return

    tool_input = data.get("tool_input", {})
    raw_path = tool_input.get("file_path", "") or tool_input.get("filePath", "")
    if not raw_path:
        return

    fp = Path(raw_path)
    if fp.suffix.lower() != ".md":
        return

    norm = raw_path.replace("\\", "/")
    if not match_any(norm, INCLUDES) or match_any(norm, EXCLUDES):
        return

    # 已寫入完成，讀回內容判斷是否已留證 / 是否機械骨架
    try:
        text = fp.read_text(encoding="utf-8")
    except Exception:
        text = ""

    if MARKER_RE.search(text):
        return  # 已過三站留證
    if SKELETON_RE.search(text):
        return  # draft-skeleton 不適用（harness 明文豁免）

    msg = (
        "[寫作 Harness 提醒] 偵測到寫作路徑中文長文且尚無三站留證："
        f"{raw_path}\n"
        f"宣告完成前須穿過 {HARNESS_PATH}："
        "S0 輸入閘（要真實素材而無 → STOP 跟需求方要，禁編造）→ "
        f"S1 機械閘（{CHECKER_PATH} exit 0）→ "
        "S2 判斷閘（結構/聲音 5 問＋敘事姿態＋台灣語感＋9 類語病，自審留證貼回覆）。"
        "三站過後於檔尾寫一行 `<!-- writing-harness: S0/S1/S2 ok YYYY-MM-DD -->`。"
        "（骨架請設 frontmatter `status: draft-skeleton` 即自動豁免。）"
    )
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": msg,
        }
    }))


if __name__ == "__main__":
    main()
