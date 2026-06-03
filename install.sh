#!/usr/bin/env bash
# writing-harness installer (macOS / Linux)
# Copies the harness into ~/.claude/skills/ so Claude Code (and the hooks) can find it.
# It does NOT touch your settings.json — see hooks/settings.example.json to wire hooks yourself.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_DIR="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"
DEST="$SKILLS_DIR/writing-harness"
TIGHTEN_DEST="$SKILLS_DIR/tighten"

echo "==> Installing writing-harness into: $DEST"
mkdir -p "$DEST" "$TIGHTEN_DEST"

cp -R "$REPO_DIR/methodology" "$DEST/"
cp -R "$REPO_DIR/scripts"     "$DEST/"
cp -R "$REPO_DIR/hooks"       "$DEST/"
cp -R "$REPO_DIR/examples"    "$DEST/"
cp    "$REPO_DIR/skill/tighten/SKILL.md" "$TIGHTEN_DEST/SKILL.md"

PYBIN="$(command -v python3 || command -v python || true)"
if [ -n "$PYBIN" ]; then
  echo "==> Running smoke tests ($PYBIN)"
  "$PYBIN" "$REPO_DIR/tests/test_harness.py" || echo "   (tests reported failures — check output above)"
else
  echo "==> Python not found on PATH; skipping smoke tests."
fi

cat <<EOF

✅ Installed.
   methodology + scripts + hooks + examples -> $DEST
   tighten skill                            -> $TIGHTEN_DEST

Next steps:
  1. Run the S1 checker on any Chinese .md:
       $PYBIN $DEST/scripts/taiwan-style-check.py your-file.md
  2. (Optional) Wire the hooks into Claude Code: open hooks/settings.example.json
     and merge its "hooks" block into ~/.claude/settings.json.
     Then edit the CONFIG block at the top of each hook to point at YOUR content
     paths (the defaults are placeholders).
  3. Read methodology/writing-harness.md — that's the 3-station method itself.
EOF
