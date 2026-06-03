#!/usr/bin/env python3
"""
verbosity-check.py — Markdown 冗贅／bloat 偵測器

純 regex，10 條規則，純 stdlib。flag 冗贅段落給後續 LLM 重寫。
原設計用於精簡 LLM 記憶／知識庫 .md，也適用任何想砍 AI slop 填充詞的 Markdown。

用法：
  python verbosity-check.py docs/*.md
  python verbosity-check.py "notes/**/*.md" --format=markdown
  python verbosity-check.py file1.md file2.md --format=json

Exit code:
  0 = 無 findings
  1 = 有 findings
  2 = 執行錯誤

規則列表（詳見 RULES dict）：
  1. frontmatter-description-echo  描述重複 name 主要字詞 >60%
  2. dated-parenthetical           body 中「（YYYY-MM-DD 補/新增/更新）」
  3. marker-prefix                 **結論** / **教訓** / **策略** 等無用前綴
  4. meta-blockquote               H1 後首段是 >分類原則/說明/規則
  5. numbered-code-comments        code block 內 ≥3 個 `# N.` 編號註解
  6. filler-words                  其實/當然/基本上/事實上...
  7. dual-preamble                 **情境**+**Pattern** 或 **方案**+**做法**
  8. h1-h2-echo                    H1 後立刻 H2 同名
  9. list-prefix-bloat             list item 以「這是/這段是/這個方案/這個功能」開頭
 10. dup-pros-apply                同節 **優點** + **適用** 雙 bullet 列
"""

import argparse
import json
import re
import sys
from glob import glob
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


FILLER_WORDS = ["其實", "當然", "基本上", "事實上", "也就是說", "換句話說", "值得一提的是", "需要注意的是"]
MARKER_PREFIXES = [r"key\s*insight", "結論", "教訓", "策略", "情境", "方案", "建議", "重點", "注意"]
META_KEYWORDS = ["分類原則", "說明", "規則", "原則"]
LIST_PREFIX_BLOAT_PATTERNS = [r"^\s*-\s+這是\s", r"^\s*-\s+這段是\s", r"^\s*-\s+這個方案\s", r"^\s*-\s+這個功能\s"]


def parse_frontmatter(lines):
    if not lines or lines[0].strip() != "---":
        return {}, 0
    fm = {}
    for i in range(1, min(len(lines), 200)):
        if lines[i].strip() == "---":
            for line in lines[1:i]:
                m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$", line)
                if m:
                    fm[m.group(1)] = m.group(2).strip()
            return fm, i + 1
    return {}, 0


def _tokens(s):
    out = []
    for ch in s:
        if "一" <= ch <= "鿿":
            out.append(ch)
    out.extend(t.lower() for t in re.findall(r"[A-Za-z0-9]+", s) if len(t) >= 2)
    return out


def rule_frontmatter_description_echo(lines, fm, fm_end):
    name = fm.get("name", "")
    desc = fm.get("description", "")
    if not name or not desc:
        return []
    name_tokens = set(_tokens(name))
    if not name_tokens:
        return []
    desc_token_set = set(_tokens(desc))
    overlap = sum(1 for t in name_tokens if t in desc_token_set)
    ratio = overlap / len(name_tokens)
    if ratio > 0.6:
        for i, l in enumerate(lines[:fm_end]):
            if l.startswith("description:"):
                return [{
                    "line": i + 1,
                    "rule": "frontmatter-description-echo",
                    "snippet": l.strip()[:100],
                    "detail": f"{overlap}/{len(name_tokens)} name tokens echoed in description"
                }]
    return []


def rule_dated_parenthetical(lines, fm_end):
    pat = re.compile(r"（\s*\d{4}-\d{2}-\d{2}\s*(?:補|新增|更新|補充)\s*）")
    findings = []
    for i in range(fm_end, len(lines)):
        if pat.search(lines[i]):
            findings.append({
                "line": i + 1,
                "rule": "dated-parenthetical",
                "snippet": lines[i].strip()[:100]
            })
    return findings


def rule_marker_prefix(lines, fm_end):
    pat = re.compile(r"^\*\*(?:" + "|".join(MARKER_PREFIXES) + r")\*\*：")
    findings = []
    for i in range(fm_end, len(lines)):
        if pat.match(lines[i]):
            findings.append({
                "line": i + 1,
                "rule": "marker-prefix",
                "snippet": lines[i].strip()[:100]
            })
    return findings


def rule_meta_blockquote(lines, fm_end):
    pat = re.compile(r"^>\s*(?:" + "|".join(META_KEYWORDS) + r")[：:]")
    findings = []
    h1_found = False
    for i in range(fm_end, len(lines)):
        if lines[i].startswith("# ") and not lines[i].startswith("## "):
            h1_found = True
            continue
        if h1_found and pat.match(lines[i]):
            findings.append({
                "line": i + 1,
                "rule": "meta-blockquote",
                "snippet": lines[i].strip()[:100]
            })
            break
    return findings


def rule_numbered_code_comments(lines, fm_end):
    findings = []
    in_code = False
    block_start = 0
    count = 0
    first_comment_line = 0
    for i in range(fm_end, len(lines)):
        if lines[i].lstrip().startswith("```"):
            if in_code:
                if count >= 3:
                    findings.append({
                        "line": first_comment_line or (block_start + 1),
                        "rule": "numbered-code-comments",
                        "snippet": f"code block L{block_start + 1}-L{i + 1}: {count} numbered comments"
                    })
                in_code = False
                count = 0
                first_comment_line = 0
            else:
                in_code = True
                block_start = i
                count = 0
                first_comment_line = 0
            continue
        if in_code and re.match(r"^\s*#\s*\d+\.", lines[i]):
            count += 1
            if first_comment_line == 0:
                first_comment_line = i + 1
    return findings


def rule_filler_words(lines, fm_end):
    pat = re.compile("|".join(FILLER_WORDS))
    findings = []
    in_code = False
    for i in range(fm_end, len(lines)):
        if lines[i].lstrip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        m = pat.search(lines[i])
        if m:
            findings.append({
                "line": i + 1,
                "rule": "filler-words",
                "snippet": lines[i].strip()[:100],
                "detail": f"matched: {m.group(0)}"
            })
    return findings


def rule_dual_preamble(lines, fm_end):
    pairs = [("情境", "Pattern"), ("方案", "做法")]
    findings = []
    for i in range(fm_end, len(lines)):
        for a, b in pairs:
            if lines[i].startswith(f"**{a}**："):
                for j in range(i + 1, min(i + 8, len(lines))):
                    if lines[j].startswith(f"**{b}**："):
                        findings.append({
                            "line": i + 1,
                            "rule": "dual-preamble",
                            "snippet": f"**{a}** L{i + 1} + **{b}** L{j + 1}"
                        })
                        break
    return findings


def rule_h1_h2_echo(lines, fm_end):
    findings = []
    for i in range(fm_end, len(lines) - 1):
        if lines[i].startswith("# ") and not lines[i].startswith("## "):
            h1_title = lines[i][2:].strip()
            for j in range(i + 1, min(i + 5, len(lines))):
                if lines[j].strip() == "":
                    continue
                if lines[j].startswith("## "):
                    h2_title = lines[j][3:].strip()
                    if h1_title == h2_title:
                        findings.append({
                            "line": j + 1,
                            "rule": "h1-h2-echo",
                            "snippet": f'H1 "{h1_title}" = H2 "{h2_title}"'
                        })
                break
    return findings


def rule_list_prefix_bloat(lines, fm_end):
    pats = [re.compile(p) for p in LIST_PREFIX_BLOAT_PATTERNS]
    findings = []
    in_code = False
    for i in range(fm_end, len(lines)):
        if lines[i].lstrip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        for p in pats:
            if p.match(lines[i]):
                findings.append({
                    "line": i + 1,
                    "rule": "list-prefix-bloat",
                    "snippet": lines[i].strip()[:100]
                })
                break
    return findings


def rule_dup_pros_apply(lines, fm_end):
    findings = []
    sections = []
    current = {"header_line": fm_end, "items": []}
    for i in range(fm_end, len(lines)):
        if re.match(r"^#{1,3} ", lines[i]):
            if current["items"]:
                sections.append(current)
            current = {"header_line": i, "items": []}
        current["items"].append((i, lines[i]))
    if current["items"]:
        sections.append(current)
    for sec in sections:
        pros_line = None
        apply_line = None
        for idx, l in sec["items"]:
            if l.startswith("**優點**"):
                pros_line = idx
            if l.startswith("**適用**"):
                apply_line = idx
        if pros_line is not None and apply_line is not None:
            findings.append({
                "line": pros_line + 1,
                "rule": "dup-pros-apply",
                "snippet": f"**優點** L{pros_line + 1} + **適用** L{apply_line + 1}"
            })
    return findings


RULE_FNS = [
    ("frontmatter-description-echo", rule_frontmatter_description_echo),
    ("dated-parenthetical", rule_dated_parenthetical),
    ("marker-prefix", rule_marker_prefix),
    ("meta-blockquote", rule_meta_blockquote),
    ("numbered-code-comments", rule_numbered_code_comments),
    ("filler-words", rule_filler_words),
    ("dual-preamble", rule_dual_preamble),
    ("h1-h2-echo", rule_h1_h2_echo),
    ("list-prefix-bloat", rule_list_prefix_bloat),
    ("dup-pros-apply", rule_dup_pros_apply),
]


def check_file(path: Path):
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as e:
        return None, str(e)
    lines = text.splitlines()
    fm, fm_end = parse_frontmatter(lines)
    findings = []
    for name, fn in RULE_FNS:
        if name == "frontmatter-description-echo":
            findings.extend(fn(lines, fm, fm_end))
        else:
            findings.extend(fn(lines, fm_end))
    findings.sort(key=lambda f: (f["line"], f["rule"]))
    return {"file": str(path).replace("\\", "/"), "total_lines": len(lines), "findings": findings}, None


def render_markdown(reports):
    out = []
    total_findings = sum(len(r["findings"]) for r in reports)
    files_with_findings = sum(1 for r in reports if r["findings"])
    out.append("# Verbosity Report")
    out.append("")
    out.append(f"Files scanned: {len(reports)} | With findings: {files_with_findings} | Total findings: {total_findings}")
    out.append("")
    rule_counts = {}
    for r in reports:
        for f in r["findings"]:
            rule_counts[f["rule"]] = rule_counts.get(f["rule"], 0) + 1
    if rule_counts:
        out.append("## Findings by rule")
        out.append("")
        for rule, count in sorted(rule_counts.items(), key=lambda x: (-x[1], x[0])):
            out.append(f"- {rule}: {count}")
        out.append("")
    for r in reports:
        if not r["findings"]:
            continue
        out.append(f"## {r['file']} ({len(r['findings'])} findings / {r['total_lines']} lines)")
        out.append("")
        for f in r["findings"]:
            detail = f" — {f['detail']}" if "detail" in f else ""
            out.append(f"- L{f['line']} `[{f['rule']}]` {f['snippet']}{detail}")
        out.append("")
    print("\n".join(out))


def expand_paths(patterns):
    files = []
    seen = set()
    for p in patterns:
        matches = glob(p, recursive=True) if any(c in p for c in "*?[") else [p]
        if not matches:
            matches = [p]
        for m in matches:
            norm = str(Path(m)).replace("\\", "/")
            if norm not in seen:
                seen.add(norm)
                files.append(m)
    return files


def main():
    ap = argparse.ArgumentParser(description="Regex-based verbosity checker for Markdown files.")
    ap.add_argument("paths", nargs="+", help=".md paths or globs")
    ap.add_argument("--format", choices=["json", "markdown"], default="json")
    args = ap.parse_args()

    files = expand_paths(args.paths)
    reports = []
    had_error = False
    for f in files:
        path = Path(f)
        if not path.exists():
            print(f"ERROR: not found: {f}", file=sys.stderr)
            had_error = True
            continue
        if not path.suffix == ".md":
            print(f"SKIP: not a .md file: {f}", file=sys.stderr)
            continue
        r, err = check_file(path)
        if err:
            print(f"ERROR: {f}: {err}", file=sys.stderr)
            had_error = True
            continue
        reports.append(r)

    if args.format == "json":
        print(json.dumps(reports, ensure_ascii=False, indent=2))
    else:
        render_markdown(reports)

    if had_error:
        sys.exit(2)
    if any(r["findings"] for r in reports):
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
