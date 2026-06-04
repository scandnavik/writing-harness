#!/usr/bin/env python3
"""Codex CLI PostToolUse adapter — writing-harness reminder (warn-only).

Codex edits files through the `apply_patch` tool (not Edit/Write), so the target
path lives inside the patch body, not in a tidy `file_path` field. We pull paths
out of the tool input/response and run the shared gate in ../harness_core.py.

Output: a non-blocking `systemMessage`. We never block (warn-only by design); a
missed path just means no reminder. Wire it up via config.example.toml.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import harness_core as core  # noqa: E402


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return

    if data.get("hook_event_name") and data["hook_event_name"] != "PostToolUse":
        return

    paths = core.collect_candidate_paths(
        data.get("tool_input") or {},
        data.get("tool_response") or {},
    )
    msgs = []
    for raw in paths:
        if not core.is_markdown(raw):
            continue
        try:
            text = Path(raw).read_text(encoding="utf-8")
        except Exception:
            text = ""
        m = core.harness_reminder(raw, text)
        if m:
            msgs.append(m)

    if msgs:
        print(json.dumps({"systemMessage": "\n\n".join(msgs)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
