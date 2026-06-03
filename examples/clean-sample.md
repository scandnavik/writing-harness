---
name: 乾淨範例
description: 示範 verbosity-check 應該 0 findings 的寫法
type: reference
---
# 一個乾淨的筆記

冗贅偵測器掃過這份檔案應該回報 0 findings。它沒有填充詞、沒有無用前綴、沒有重複框架，也沒有 description 回聲。

每個段落直接講事情，不先宣告「這是一段說明」再說明。清單項直接給內容：

- 規則庫只升不降，靠機械閘把新錯誤固化成程式
- 判斷閘留證，逐題自答貼回覆
- 編造在輸入閘就被擋掉

程式碼區塊也保持乾淨，不堆編號註解：

```python
def gate(draft_path):
    result = run_checker(draft_path)
    return result.exit_code == 0
```

收尾就停，沒有空心金句。
