---
name: tighten
description: >
  偵測並重寫 Markdown 的冗贅用詞。純 regex 先掃 10 條 bloat pattern，再用
  sonnet sub-agent 重寫 flagged 段落。觸發：「幫我精簡」「砍冗贅」「tighten」
  「檢查用詞」「token 節省」，或呼叫 /tighten [paths]。
---

# Tighten

Markdown 精簡管線，目的是省 token。分工是這樣：偵測交給腳本（不花 LLM），只有重寫才動用 LLM，避免把便宜的偵測工作浪費在昂貴的模型上。

bloat（填充詞、無用前綴、重複框架、description 回聲）是 AI slop 的另一張臉：不是寫錯，是寫太多、講太繞。這支 skill 把「偵測」交給純 regex（零 LLM），只把「重寫」交給 LLM，最省 token。

## 預設行為

| 輸入 | 預設掃描路徑 |
|------|-------------|
| 無參數 | `**/*.md`（排除你指定的 index／生成檔） |
| 單一路徑 | 該檔或該 glob |
| 多路徑 | 全部納入 |

**建議絕不碰**：結構敏感的索引檔（手工維護的目錄）、機器生成的 yaml、工具腳本目錄。把這些路徑加進你自己的排除清單。

## 10 條規則（詳見 scripts/verbosity-check.py）

| # | 規則 | 一句話 |
|---|------|--------|
| 1 | frontmatter-description-echo | description 重複 name 字詞 >60% |
| 2 | dated-parenthetical | body 中「（YYYY-MM-DD 補）」冗贅 |
| 3 | marker-prefix | **結論** / **教訓** / **策略** 等無用前綴 |
| 4 | meta-blockquote | H1 後首段 `> 分類原則/說明/規則` |
| 5 | numbered-code-comments | code block ≥3 個 `# N.` 編號註解 |
| 6 | filler-words | 其實/當然/基本上/事實上... |
| 7 | dual-preamble | **情境**+**Pattern** 或 **方案**+**做法** |
| 8 | h1-h2-echo | H1 後立刻 H2 同名 |
| 9 | list-prefix-bloat | list 以「這是/這段是/這個方案/這個功能」開頭 |
| 10 | dup-pros-apply | 同節 **優點** + **適用** 雙 bullet 列 |

## 執行流程

### Step 1 — 執行偵測腳本

```bash
python ~/.claude/skills/writing-harness/scripts/verbosity-check.py <paths> --format=markdown
```

讀 exit code：
- `0` → 回報「檔案已足夠精簡」，退出
- `1` → 繼續 Step 2
- `2` → 回報錯誤，退出

### Step 2 — 呈現 report 並問核准

把 markdown report 貼給用戶，附一行摘要：

```
共 N 處命中、散佈在 M 個檔案。各規則命中次數：<rule>: <count>, ...
要重寫嗎？(y / n / 指定檔案子集)
```

等待用戶回應。

### Step 3 — 派 sonnet sub-agent 重寫

對每一個有 findings 的檔案（依用戶選的子集），spawn 一個 `general-purpose` agent（`model: sonnet`）。

**Agent prompt 模板**：

```
你是精簡寫手。下方 .md 檔的特定段落被標記為冗贅（偵測規則、行號、snippet）。

任務：只修 flagged 段落，其餘原封不動。

硬性約束：
1. 不動 frontmatter 的 name / type / 任何系統欄位
2. frontmatter 的 description 可改（若被 flagged 為 description-echo）
3. 保留所有 markdown links `[text](path)`、code blocks、table 結構
4. 不新增段落、不改 H1 標題
5. 語意等價：每條資訊都要留，只砍表達
6. 不確定時 → 保留原文（寧願 under-cut 不要 over-cut）

規則對照：
- marker-prefix：刪掉「**結論**：」「**教訓**：」等前綴，保留後面的內容
- dated-parenthetical：刪掉「（YYYY-MM-DD 補）」這類標記
- filler-words：刪「其實/當然/基本上」等空泛修飾
- meta-blockquote：刪掉整行 `> 分類原則：...`
- dual-preamble：兩段合併為一句開場
- h1-h2-echo：刪掉重複的 H2 或改成細節標題
- list-prefix-bloat：刪「- 這是 / - 這段是」開頭的冗贅
- numbered-code-comments：code 內 `# 1. # 2. # 3.` 保留 1-2 個關鍵註解即可
- dup-pros-apply：flag 即可，若語意真的重疊才合併；否則保留
- frontmatter-description-echo：重寫 description 講「這份文件提供什麼」（不重複 name）

輸出：直接用 Edit/Write 改檔，不要回文字報告。改完後用一句話說「<file> 已精簡」。

檔案路徑：<path>
Findings：
<list of findings with line + rule + snippet>
```

### Step 4 — 重跑腳本驗證

```bash
python ~/.claude/skills/writing-harness/scripts/verbosity-check.py <paths> --format=json
```

比對 before/after findings 數，若某檔 findings 沒減（或反增）→ 標記該檔為「重寫失敗」，但**不自動還原**（git diff 讓用戶自己看）。

### Step 5 — 彙總報告

格式：

```
Tighten 完成

| 檔案 | 行數 before→after | findings before→after |
|------|-------------------|----------------------|
| ... | ... | ... |

Token 估算節省：~<行數差 × 20> tokens
```

## 邊界

- **不碰結構敏感索引檔**：手工維護的目錄結構不該被自動重寫
- **不裝依賴**：腳本純 stdlib
- **重寫失敗原檔不動**：git 還在，用戶自己 `git diff` 看
- **under-cut prior**：LLM 判斷模糊時保留原文

## 驗收範例

```bash
# 用本 repo 附的 fixture 驗證偵測器
python ~/.claude/skills/writing-harness/scripts/verbosity-check.py examples/bloated-sample.md --format=markdown   # 應該大量命中
python ~/.claude/skills/writing-harness/scripts/verbosity-check.py examples/clean-sample.md --format=markdown     # 應該 0 findings
```
