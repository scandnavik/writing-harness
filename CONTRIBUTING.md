# Contributing

Thanks for wanting to improve writing-harness. This project has one design principle that shapes everything: **the rule base only goes up, never down (a ratchet).** Read that before you open a PR.

歡迎貢獻。請先理解這套系統唯一的設計信條：**規則庫只升不降（像棘輪，那種只能單向轉、卡住就不會倒退的齒輪）。** 每抓到一個新的壞味道，就把它固化成一道閘，下次再也漏不掉。

---

## The ratchet: where does a new rule go?

抓到一個 LLM 反覆寫出的壞味道時，先問一個問題：**正則抓得到嗎？**

- **抓得到（機械可檢，就是寫得出正則）** → 加進 `scripts/taiwan-style-check.py`（或 `verbosity-check.py`）的常數區，配一個檢查函式（check function）。這是首選路徑。
- **抓不到（要看上下文／要人判斷）** → 寫進 `methodology/writing-harness.md` 的 S2 判斷項，或 `methodology/taiwan-writing-glossary.md` 的對照表。

預設動作是「加機械閘」。留成 prose 規則是例外，而且要說得出為什麼正則必然誤判。

> 為什麼這樣分：機械閘是會執行的測試（exit code 不會說謊），prose 規則是要靠人記得的承諾。能變成測試的就別留成承諾。

---

## 加一條機械規則的步驟

以「新增一個禁用詞」為例：

1. 在 `scripts/taiwan-style-check.py` 對應的常數 list 加一行（例如 `MAINLAND_WORDS`、`URGENCY_WORDS`、`CONCLUSION_LEAD_NOISE`）。
2. 如果是新類別，仿照現有的 `check_*` function 寫一個，並在 `main()` 的 `results` dict 掛上。
3. 在 `examples/bloated-sample.md` 補一行會命中新規則的內容，確認這個測試樣本（fixture）仍會 fail。
4. 在 `tests/test_harness.py` 補一個 case（clean 不該命中、bad 應該命中）。
5. 跑 `python tests/test_harness.py`，全綠才送 PR。
6. 同步更新 `methodology/taiwan-writing-glossary.md`，讓人讀的規則手冊與腳本一致。

腳本與 glossary 必須同步，這是硬要求。腳本是執法者，glossary 是法條，兩個對不上就是 bug。

---

## 加一條 glossary 規則（人判類）

直接編 `methodology/taiwan-writing-glossary.md`：

- 新詞 → §2.1 表加 row
- 偏陸動詞 → §2.2 表加 row
- 句型／結構 → §4 加節
- 不確定要不要正式收 → 先放檔尾「驗證期」段，觀察一段時間無推翻再升正式條目

---

## 回饋迴路：讓真人改稿餵養規則

`scripts/rewrite-diff.py` 是設計來吃「真人 post-edit」的。流程：

```bash
python scripts/rewrite-diff.py 你的草稿.md 真人改完的版本.md
```

它會統計真人改了哪幾類。同一類被改 3 次以上，那條規則就該進 glossary（理想上進腳本）。這是這套系統自我增強的方式：人改一次，系統學一次，下次自己擋。

---

## 本機開發

```bash
python tests/test_harness.py     # 煙霧測試，純 stdlib，零依賴
```

不引入任何第三方套件。所有腳本必須維持純 stdlib，這樣任何環境、任何 CI 都能直接跑。

---

## 換到別的語境（簡中／港繁／純書面）

方法論（三站）與語言無關，要換的只有 glossary 與腳本常數。見 [`examples/glossary-zh-cn.example.md`](examples/glossary-zh-cn.example.md) 的 worked example。歡迎以 PR 貢獻其他語境的 glossary variant（放 `examples/glossary-<locale>.example.md`）。

---

## PR checklist

- [ ] `python tests/test_harness.py` 全綠
- [ ] 腳本改動有對應的測試樣本（fixture）＋測試案例（test case）
- [ ] 腳本與 glossary 同步
- [ ] 沒有夾帶任何私有資料（真名、客戶、本機路徑）
