---
description: Detect and rewrite verbose Markdown (writing-harness tighten gate).
argument-hint: "[paths...]"
---

You are running the **tighten** pipeline from writing-harness. Detection is pure
regex (zero LLM); only the rewrite step uses the model.

Codex has no skill system, so this custom prompt is the Codex-native way to
invoke tighten. Drop this file at `~/.codex/prompts/tighten.md`, then run
`/tighten` (optionally with paths) in Codex.

## Steps

1. Run the detector (replace the path with your clone location):

   ```bash
   python3 /ABS/PATH/TO/writing-harness/scripts/verbosity-check.py $ARGUMENTS --format=markdown
   ```

   - exit `0` → report "already tight enough", stop.
   - exit `1` → continue.
   - exit `2` → report the error, stop.

2. Show the markdown report and ask for approval, with a one-line summary:
   `N hits across M files. Rewrite? (y / n / subset of files)`

3. On approval, rewrite ONLY the flagged spans, file by file. Hard constraints:
   - Don't touch frontmatter `name` / system fields (the `description` may be
     rewritten if flagged as description-echo).
   - Preserve all markdown links, code blocks, and table structure.
   - No new paragraphs, don't change H1.
   - Semantic equivalence: keep every piece of information, cut only wording.
   - When unsure, keep the original (prefer under-cutting).

4. Re-run the detector in `--format=json` to verify findings dropped. If a file
   didn't improve, flag it as "rewrite failed" but DON'T auto-revert (leave it
   for `git diff`).

5. Summarize: per-file line and findings before→after.

Full rule reference: `scripts/verbosity-check.py` and `skill/tighten/SKILL.md`.
