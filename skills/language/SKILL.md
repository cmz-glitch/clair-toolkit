---
name: language
description: Detect TR, EN, FR, AR, or ZH for the thread-language rule.
---

# Thread language

Use before drafting, on the earlier messages in the thread.

```
python -m clair_toolkit lang --text "..."
python -m clair_toolkit lang FILE
```

`{"lang":"TR"}` (or EN, FR, AR, ZH). `unknown` means there was not enough text; ask which language before drafting. The draft must use this language. Milou's dictation language is not the send language.
