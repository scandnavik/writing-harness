#!/usr/bin/env python3
"""Hermes Agent plugin — writing-harness reminders (warn-only).

Install: copy this file (and ../harness_core.py) into ~/.hermes/plugins/, or
symlink it there. Hermes discovers any module exposing `register(ctx)`.

Why two hooks instead of one
----------------------------
Hermes `post_tool_call` is fire-and-forget: its return value is ignored and it
cannot inject context back to the agent. So we can't remind from there directly.
The idiomatic Hermes pattern is:

  1. `post_tool_call` OBSERVES each tool result, and stashes any reminder it
     finds into a small in-process queue (a side effect — which is all
     post_tool_call is allowed to do).
  2. `pre_llm_call` (whose return value CAN inject context) drains that queue on
     the next model turn and feeds the reminder in as context.

Both gates live in ../harness_core.py, shared with the Codex adapters and
mirroring the Claude Code hooks.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import harness_core as core  # noqa: E402

# Reminders observed in post_tool_call, waiting to be injected on the next turn.
_pending: list[str] = []


def _on_post_tool(**kwargs) -> None:
    """post_tool_call(tool_name, args, result, task_id, duration_ms, **kwargs).

    Hermes invokes hooks by keyword, so **kwargs is the safe, forward-compatible
    signature. We only need args + result to find the written file(s).
    """
    args = kwargs.get("args") or {}
    result = kwargs.get("result") or ""
    paths = core.collect_candidate_paths(args, result)
    for msg in core.reminders_for_paths(paths):
        if msg not in _pending:
            _pending.append(msg)


def _inject_pending(**kwargs):
    """pre_llm_call hook. Return value is injected as context for this turn.

    Returns {"context": str} when there's a pending reminder, else None (which
    leaves the turn unchanged).
    """
    if not _pending:
        return None
    msg = "\n\n".join(_pending)
    _pending.clear()
    return {"context": "[writing-harness]\n" + msg}


def register(ctx) -> None:
    ctx.register_hook("post_tool_call", _on_post_tool)
    ctx.register_hook("pre_llm_call", _inject_pending)
