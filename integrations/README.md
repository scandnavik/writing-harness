# Integrations — 接到不同的 agent

> One harness, many agents. The methodology and scripts are agent-agnostic; only
> the auto-reminder wiring and the skill packaging differ per host.

這套 harness 大部分本來就跟 agent 無關。真正綁定某個 agent 的只有兩件事：**自動提醒的接線方式**，和 **tighten 怎麼被叫起來**。其餘——三站方法論（markdown）和檢查腳本（純 stdlib Python）——任何 agent、任何編輯器、任何 CI 都能直接用。

## 哪些東西本來就到處能用（不必接）

| 元件 | 怎麼用 |
|---|---|
| `methodology/writing-harness.md`、`taiwan-writing-glossary.md` | 任何 agent 讀得懂的 markdown。放進該 agent 的「自訂指令」即可（見下表）。 |
| `scripts/taiwan-style-check.py`、`verbosity-check.py` | 純 stdlib，`python <script> file.md`。任何環境跑得動，零依賴。 |

換句話說：要讓任何 agent「會跑 S1 機械閘」，根本不必接線——叫它跑那支腳本就好。下面要接的，是讓 agent **自動**在你寫長文時提醒你（不必每次手動），以及把 tighten 變成原生指令。

## 三個 agent 的接線對照

| 能力 | Claude Code | OpenAI Codex CLI | NousResearch Hermes |
|---|---|---|---|
| 寫完自動提醒三站 | `hooks/` PostToolUse hook（`Edit\|Write`） | `integrations/codex/` 的 hook（`apply_patch`） | `integrations/hermes/` plugin（`post_tool_call`＋`pre_llm_call`） |
| 對外產出 evidence 提醒 | `hooks/output-tier-gate.py` | `integrations/codex/output-tier-gate.py` | 同上 plugin 一併處理 |
| 方法論餵給 agent | skill 載入 + CLAUDE.md | `AGENTS.md`（`~/.codex/AGENTS.md` 或專案根） | `AGENTS.md` / `CLAUDE.md` / `SOUL.md` |
| tighten 叫法 | `skill/tighten/SKILL.md`（skill） | `~/.codex/prompts/tighten.md`（custom prompt，本目錄附） | `~/.hermes/skills/tighten/SKILL.md`（同 SKILL.md 標準） |

提醒類 hook 一律 **warn-only**：只提醒不擋。觀察一陣子誤報乾淨後，再自行升級成硬擋。

---

## Codex CLI

1. Clone 這個 repo 到任意位置，記下絕對路徑。
2. 把 `integrations/codex/config.example.toml` 的 `hooks` 區塊併進 `~/.codex/config.toml`（或專案的 `.codex/config.toml`），把 `/ABS/PATH/TO/writing-harness` 換成你的 clone 路徑。
3. （可選）把 `integrations/codex/prompts/tighten.md` 複製到 `~/.codex/prompts/tighten.md`，之後 `/tighten` 就能用。
4. （可選）把 `methodology/writing-harness.md` 的精華貼進 `~/.codex/AGENTS.md`，讓 Codex 預設就知道三站規則。

**為什麼 matcher 是 `apply_patch`**：Codex 改檔走 `apply_patch` 工具，不是 `Edit`/`Write`，檔名藏在 patch 內文（`*** Update File: ...`）。adapter 會自動從 patch 裡撈路徑，所以你不必改 matcher。輸出走 Codex 的 `systemMessage` 欄位（非阻擋）。

## Hermes Agent

1. 把 `integrations/hermes/writing_harness_plugin.py` 和 `integrations/harness_core.py` 一起放進 `~/.hermes/plugins/`（plugin 會 import 同層的 core，所以兩個要在一起，或自行調整 import 路徑）。
2. tighten：把 `skill/tighten/SKILL.md` 複製到 `~/.hermes/skills/tighten/SKILL.md`。frontmatter（`name`／`description`）就是 agentskills.io 標準，Hermes 直接吃；只要把內文寫死的 `~/.claude/...` 路徑改成你的 clone 路徑、把「spawn general-purpose agent」換成 Hermes 的 subagent 叫法即可。
3. （可選）把方法論精華放進 `~/.hermes/`（或專案）的 `AGENTS.md` / `CLAUDE.md`。

**為什麼是兩個 hook**：Hermes 的 `post_tool_call` 是 fire-and-forget——return 值被忽略、不能回注 context。所以 plugin 在 `post_tool_call` 只負責「觀察 + 暫存提醒」，真正把提醒注入下一輪對話的是 `pre_llm_call`（它的 return 值可注入 context）。這是 Hermes 慣用法，細節見 plugin 檔頂註解。

## Claude Code

不在這個目錄——它用的是 repo 根的 `hooks/`，接法見最上層 `README.md` 的「接進 Claude Code」。

---

## 共用核心與設定家

`harness_core.py` 是 Codex / Hermes 兩邊 adapter 共用的決策核心（純 stdlib）：要不要提醒、提醒什麼，都集中在這裡，改規則只改一處。Codex／Hermes 使用者要調整偵測路徑（`INCLUDES` / `EXCLUDES` / `L3_*`）就改 `harness_core.py` 頂部的 CONFIG。

Claude Code 的 `hooks/` 刻意保留各自獨立的同款 CONFIG，**不動它**是為了讓既有安裝零風險。如果你想讓三個 agent 共用同一份設定，把 `hooks/` 那兩支也指到 `harness_core.py` 即可（regex 與訊息完全一致）。
