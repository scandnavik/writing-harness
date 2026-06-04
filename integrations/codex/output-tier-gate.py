#!/usr/bin/env python3
"""Codex CLI PostToolUse adapter — outbound-deliverable tier gate (warn-only).

When Codex writes a file under a client-facing / outbound root (L3), inject a
reminder to attach an evidence pack. Same logic as the Claude output-tier hook,
adapted to Codex's apply_patch input and `systemMessage` output channel.
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
        m = core.tier_reminder(raw)
        if m:
            msgs.append(m)

    if msgs:
        print(json.dumps({"systemMessage": "\n\n".join(msgs)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
