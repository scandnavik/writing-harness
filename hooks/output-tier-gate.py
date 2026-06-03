#!/usr/bin/env python3
"""Outbound-deliverable tier gate (PostToolUse, warn-only).

When you write a file that will go to a client / external audience (L3), inject
a reminder to attach an evidence pack: reproducibility, citable sources,
spot-check coverage, and a human review point. This is the "don't ship AI slop
to a paying client without evidence" guardrail.

Tiers:
  L3 = real client files / outbound proposals -> evidence-pack reminder
  L2 = content production / course drafts      -> light reminder (off by default)
  L1 = internal notes, indexes, scratch        -> never interrupt

==============================================================================
CONFIGURE THIS — L3_INCLUDES should match the paths where client-facing /
outbound deliverables live. L3_EXCLUDES carves out internal working sub-paths
(intake, payment, README, registries...) that match L3 but shouldn't fire.
Patterns are regex. The examples below use placeholder folder names — replace
`ClientA|ClientB` etc. with your own, or keep the generic folder patterns.
==============================================================================
"""
import json
import re
import sys


# --- CONFIG: outbound / client-facing roots ---
L3_INCLUDES = [
    r"clients[/\\]",                 # e.g. clients/<name>/
    r"proposals[/\\]",               # e.g. proposals/
    r"deliverables[/\\]",            # e.g. deliverables/
    # name-specific example (replace with your real client folder names):
    # r"projects[/\\](ClientA|ClientB|ClientC)",
]

# --- CONFIG: internal sub-paths to skip even if they match L3_INCLUDES ---
L3_EXCLUDES = [
    r"[/\\](consent|intake|internal|sessions)[/\\]",  # internal working subdirs
    r"[/\\]payment[/\\]",                              # money workspace
    r"[/\\]CHANGELOG\.md$",
    r"[/\\]README\.md$",
    r"[/\\]_registry[/\\]",
    r"[/\\]raw[/\\]",
    r"[/\\]\.gitignore$",
]

# --- CONFIG (optional second stage, off by default) ---
# L2_INCLUDES = [
#     r"content[/\\]",
#     r"courses[/\\]",
# ]
# ==============================================================================


def match_any(path: str, patterns) -> bool:
    return any(re.search(p, path) for p in patterns)


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return

    tool_input = data.get("tool_input", {})
    path = tool_input.get("file_path", "") or tool_input.get("filePath", "")
    if not path:
        return

    msg = None
    if match_any(path, L3_INCLUDES) and not match_any(path, L3_EXCLUDES):
        msg = (
            "[L3 對外產出偵測] 此檔將給客戶/外部看。請附 evidence pack："
            "(1) 同題重跑穩定度 (2) 引用可查 (3) 抽查覆核率 (4) 人類覆核點。"
            "無法立即附請在文件頂部標 `TODO: evidence`。"
        )
    # elif match_any(path, L2_INCLUDES):
    #     msg = "[L2 對外發布前] 確認：引用回查、語氣校準、台灣用語。"

    if msg:
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": msg,
            }
        }))


if __name__ == "__main__":
    main()
