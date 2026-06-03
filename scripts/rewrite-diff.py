#!/usr/bin/env python3
"""Harness feedback loop: analyze rewrite diff between draft and final.

Detects systematic style deviations (what a human post-editor consistently
fixes) so the glossary / style rules can be updated. Run it after a human
post-edits your draft: if the same category shows up 3+ times, that rule
belongs in the glossary.

Usage:
    python rewrite-diff.py <draft.md> <final.md>

Exit codes:
    0   - diff analysis completed
    2   - usage error
"""
from __future__ import annotations

import difflib
import re
import sys
from pathlib import Path


STYLE_PATTERNS = {
    "英文詞中文化": [
        (r"\bticket\b", "任務"),
        (r"\bbug\b", "任務"),
        (r"\bprompt\b", "提示詞"),
        (r"\bcode\b", "程式碼"),
        (r"\bjunior\b", "初階"),
        (r"tech\s+guy", "科技人"),
        (r"low\s+context", "沒什麼經驗"),
    ],
    "小結標記移除": [
        (r"\*\*小結[:：]", ""),
        (r"\*\*Takeaway[:：]", ""),
        (r"\*\*重點[:：]", ""),
    ],
    "引導語刪除": [
        (r"第[一二三四五六七八九十]個(趨勢|發現|觀察|重點)", ""),
    ],
    "解說員句刪除": [
        (r"這就是.*?的形狀", ""),
        (r"這對應到", ""),
        (r"這顯示", ""),
    ],
    "破折號改寫": [
        (r"——", ""),
    ],
    "推銷詞刪除": [
        (r"該停下來看", ""),
        (r"值得重視", ""),
        (r"不可不知", ""),
    ],
}


def strip_frontmatter(content):
    if content.startswith("---\n"):
        parts = content.split("\n---\n", 1)
        if len(parts) == 2:
            return parts[1]
    return content


def load(path):
    return strip_frontmatter(Path(path).read_text(encoding="utf-8"))


def classify_change(old_line, new_line):
    """Classify a diff change by style category."""
    hits = []
    for category, patterns in STYLE_PATTERNS.items():
        for pattern, _ in patterns:
            # Detected in old but not new = removed
            if re.search(pattern, old_line, re.IGNORECASE) and not re.search(
                pattern, new_line, re.IGNORECASE
            ):
                hits.append(category)
                break
    return hits


def main():
    if len(sys.argv) != 3:
        print("Usage: rewrite-diff.py <draft.md> <final.md>", file=sys.stderr)
        return 2

    draft_path = Path(sys.argv[1])
    final_path = Path(sys.argv[2])

    if not draft_path.exists() or not final_path.exists():
        print(f"File not found: {draft_path} or {final_path}", file=sys.stderr)
        return 2

    draft = load(draft_path).splitlines(keepends=False)
    final = load(final_path).splitlines(keepends=False)

    diff = list(
        difflib.unified_diff(
            draft, final, lineterm="", fromfile=str(draft_path.name), tofile=str(final_path.name)
        )
    )

    deleted = [d[1:] for d in diff if d.startswith("-") and not d.startswith("---")]
    added = [d[1:] for d in diff if d.startswith("+") and not d.startswith("+++")]

    # Heuristic categorization
    category_counts = {cat: 0 for cat in STYLE_PATTERNS}
    samples = {cat: [] for cat in STYLE_PATTERNS}

    # For removed lines, check if any style pattern was present in draft
    for line in deleted:
        for category, patterns in STYLE_PATTERNS.items():
            for pattern, _ in patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    category_counts[category] += 1
                    if len(samples[category]) < 3:
                        samples[category].append(line.strip()[:80])
                    break

    # Overall stats
    total_deleted = len(deleted)
    total_added = len(added)

    print(f"# Rewrite Diff 分析")
    print(f"\n- 原稿：`{draft_path.name}`（{len(draft)} 行正文）")
    print(f"- 改寫版：`{final_path.name}`（{len(final)} 行正文）")
    print(f"- 刪除：{total_deleted} 行")
    print(f"- 新增：{total_added} 行")
    print()

    print("## 按類型統計（以刪除行偵測到的 style pattern 為主）\n")
    print("| 類型 | 命中次數 | 範例 |")
    print("|------|---------|------|")
    total_hits = 0
    for cat, count in category_counts.items():
        total_hits += count
        if count > 0:
            example = samples[cat][0] if samples[cat] else ""
            print(f"| {cat} | {count} | `{example}` |")

    print()
    if total_hits == 0:
        print("**無明顯 style 偏差類型**（純事實修正或重組）")
    else:
        print("## 建議行動\n")
        high_freq = [cat for cat, count in category_counts.items() if count >= 3]
        if high_freq:
            print("以下類型出現 ≥3 次，**應把對應規則寫進 glossary（taiwan-writing-glossary.md）**：")
            for cat in high_freq:
                print(f"- {cat}（{category_counts[cat]} 處）")
        else:
            print("單類型命中 <3 次，不強制更新規則。若想累積 pattern，可手動記錄。")

    print()
    print("## Unified diff（參考）\n")
    print("```diff")
    for line in diff[:80]:
        print(line)
    if len(diff) > 80:
        print(f"... （{len(diff)} 行 diff，顯示前 80 行）")
    print("```")

    return 0


if __name__ == "__main__":
    sys.exit(main())
