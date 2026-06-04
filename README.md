# writing-harness

> A quality gate that stops an LLM from shipping "AI slop" in Chinese long-form writing. Three stations: an input gate, a mechanical regex gate, and a human-judgment gate with mandatory self-attestation.

防 AI Slop 的一套寫作品質閘（AI Slop 指 AI 寫出來那種空泛、堆砌、一看就知道不是人寫的味道）。它把「會不會寫成 AI 腔」這件事，從事後憑感覺修，前移成動筆前、草稿後兩個固定檢查點。方法論、腳本、Claude Code hook 三件一起給，別人 clone 下來就能套用。

針對**台灣繁體中文**語境調校，但方法論本身與語言無關，換個 glossary 就能搬到別的語境。

---

## 這套系統在解決什麼

LLM 寫中文長文有一組穩定的壞味道：半形標點夾在中文裡、破折號氾濫、陸用詞、「不是 X，是 Y」的二元對比模板、句首「其實／老實說」這類零承載的填充、煞有介事編一個假例子。這些合起來就是 AI slop。

靠 prompt 寫幾條規則擋不住，因為模型會選擇性遵守，而且事後沒有證據能證明它真的做了。這套系統改用「閘」的設計：機械的部分交給程式（exit code 不會說謊），判斷的部分強制留證（逐題自答貼回覆），而且規則庫只升不降。

## 系統三層

| 層 | 檔案 | 角色 |
|---|---|---|
| **方法論** | `methodology/writing-harness.md` | S0 輸入閘 / S1 機械閘 / S2 判斷閘，三站本體 |
| | `methodology/taiwan-writing-glossary.md` | 規則手冊：標點、陸→台用字、句型、術語白話化 |
| **機械閘腳本** | `scripts/taiwan-style-check.py` | S1 主閘，掃 11 類硬規則（exit 0／10） |
| | `scripts/verbosity-check.py` | 掃 10 條 bloat／冗贅 pattern |
| | `scripts/rewrite-diff.py` | 比對草稿與真人改稿，找出該寫進 glossary 的規則 |
| **自動執行 Hook** | `hooks/writing-harness-gate.py` | PostToolUse 自動提醒「這篇還沒過三站」 |
| | `hooks/output-tier-gate.py` | 對外產出自動提醒附佐證包：來源、抽查、人工複核 |
| **Skill** | `skill/tighten/SKILL.md` | bloat 偵測加 LLM 重寫管線 |
| **範本** | `examples/content-voice-prompt.template.md` | 填空式的「你自己的口吻」規格 |

## 快速安裝

```bash
git clone https://github.com/scandnavik/writing-harness.git
cd writing-harness

# macOS / Linux
./install.sh

# Windows (PowerShell)
.\install.ps1
```

安裝腳本會把方法論、腳本、hook、範本複製到 `~/.claude/skills/writing-harness/`，把 tighten skill 複製到 `~/.claude/skills/tighten/`，並跑一次煙霧測試（最基本的「裝完到底能不能動」檢查）。它**不會動你的 settings.json**，hook 接線要你自己來（見下）。

## 三分鐘上手

### 1. 跑機械閘（不裝任何東西就能用）

```bash
python scripts/taiwan-style-check.py 你的文章.md
```

exit 0 代表過；exit 10 會列出每一條命中與行號。這支腳本零依賴、純 stdlib，任何編輯器、任何 agent、CI 都能接。

### 2. 跑完整三站

打開 `methodology/writing-harness.md`，照 S0（動筆前要真素材）、S1（跑上面那支腳本到 exit 0）、S2（5 問加敘事姿態加 9 類語病，逐題自答留證）走一遍。完成時在檔尾寫一行留證標記。

### 3. 砍冗贅

```bash
python scripts/verbosity-check.py "你的筆記/**/*.md" --format=markdown
```

偵測歸偵測，重寫交給 `skill/tighten/` 那支 skill 派 LLM 做（偵測零 LLM token，只有重寫才花）。

## 接進 Claude Code（讓它自動提醒）

把 `hooks/settings.example.json` 裡的 `hooks` 區塊併進你的 `~/.claude/settings.json`，然後**改每個 hook 檔頂部的 CONFIG 區塊**，把路徑指到你自己放長文的目錄（預設值是 placeholder）。接好以後，每次寫到那些路徑的中文長文，Claude Code 會自動提醒你還沒過三站。

兩個 hook 都是 warn-only（只提醒不擋），觀察誤報乾淨後，你可以自己升級成硬擋的 Stop hook。

## 客製到你的語境

- **換語言／地區**：`taiwan-writing-glossary.md` 的 §2 對照表整段換成你那邊的判準（簡中、港繁、純學術書面都行），三站方法論不動。完整 worked example 見 [`examples/glossary-zh-cn.example.md`](examples/glossary-zh-cn.example.md)（把規則分成「通用保留／需翻轉／需調整」三類，附可直接貼的腳本常數）。
- **改機械規則**：規則都集中在 `scripts/taiwan-style-check.py` 頂部的常數區（陸用詞、禁用句型、雜訊框架詞），加減一行就改了行為。
- **你自己的口吻**：複製 `examples/content-voice-prompt.template.md`，把 `<填你的>` 換成你的範例。這是 S2 判斷「像不像你」要比對的那把尺。

## Harness 與 checklist 的差別

checklist 是給人看的承諾，harness 是會執行的系統。差別有三：

1. **機械閘是程式，不是承諾**：跑不過就是跑不過，沒得通融。
2. **判斷閘要留證**：自答結果貼出來，事後可以查核。
3. **規則庫只升不降**：每次被真人改稿揪出的新壞味道，先問「正則抓得到嗎」，抓得到就往 S1 腳本補一條，抓不到才寫成 S2 的判斷項。

規則庫就這樣單向長大，品質地板只升不降。

## 目錄結構

```
writing-harness/
├─ methodology/        三站方法論 + glossary 規則手冊
├─ scripts/            3 支純 stdlib 檢查腳本
├─ hooks/              2 個 Claude Code PostToolUse hook + settings 範例
├─ skill/tighten/      bloat-busting skill
├─ examples/           語感範本 + 兩個測試樣本（一個全是壞味道、一個乾淨）
├─ tests/              煙霧測試
├─ install.sh          macOS/Linux 安裝
└─ install.ps1         Windows 安裝
```

## 測試

```bash
python tests/test_harness.py
```

## Contributing

歡迎貢獻規則與其他語境的 glossary。核心信條是「閘只升不降」，詳見 [CONTRIBUTING.md](CONTRIBUTING.md)。

## License

MIT，見 [LICENSE](LICENSE)。
