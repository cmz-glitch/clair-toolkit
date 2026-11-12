---
name: sent-dup
description: Flag an earlier Sent message to the same address or company domain.
---

# Sent duplicate check

Use before a new outbound to a recipient, after exporting Sent to JSON.

```
python -m clair_toolkit sent-dup SENT.json --to EMAIL [--to EMAIL] [--subject TEXT] [--keyword WORD]
```

`hit: false` means no earlier send matched. Each match has `email`, `via` (`address` or `domain`), `id`, `date`, and `subject`. The same address always counts. The same domain counts for company domains. Gmail, Outlook, Yahoo, iCloud, and the other public mail hosts do not count as a domain hit. `--subject` and `--keyword` both have to match when you pass them.
