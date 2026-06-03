# writing-harness installer (Windows / PowerShell)
# Copies the harness into ~\.claude\skills\ so Claude Code (and the hooks) can find it.
# It does NOT touch your settings.json — see hooks\settings.example.json to wire hooks yourself.
$ErrorActionPreference = "Stop"

$RepoDir   = $PSScriptRoot
$SkillsDir = if ($env:CLAUDE_SKILLS_DIR) { $env:CLAUDE_SKILLS_DIR } else { Join-Path $HOME ".claude\skills" }
$Dest        = Join-Path $SkillsDir "writing-harness"
$TightenDest = Join-Path $SkillsDir "tighten"

Write-Host "==> Installing writing-harness into: $Dest"
New-Item -ItemType Directory -Force -Path $Dest, $TightenDest | Out-Null

foreach ($sub in @("methodology", "scripts", "hooks", "examples")) {
    Copy-Item -Recurse -Force (Join-Path $RepoDir $sub) (Join-Path $Dest $sub)
}
Copy-Item -Force (Join-Path $RepoDir "skill\tighten\SKILL.md") (Join-Path $TightenDest "SKILL.md")

$Py = (Get-Command python -ErrorAction SilentlyContinue)
if ($Py) {
    Write-Host "==> Running smoke tests"
    & python (Join-Path $RepoDir "tests\test_harness.py")
} else {
    Write-Host "==> Python not found on PATH; skipping smoke tests."
}

Write-Host ""
Write-Host "Installed." -ForegroundColor Green
Write-Host "   methodology + scripts + hooks + examples -> $Dest"
Write-Host "   tighten skill                            -> $TightenDest"
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Run the S1 checker on any Chinese .md:"
Write-Host "       python $Dest\scripts\taiwan-style-check.py your-file.md"
Write-Host "  2. (Optional) Wire the hooks into Claude Code: open hooks\settings.example.json"
Write-Host "     and merge its 'hooks' block into ~\.claude\settings.json."
Write-Host "     Then edit the CONFIG block at the top of each hook to point at YOUR content paths."
Write-Host "  3. Read methodology\writing-harness.md — that's the 3-station method itself."
