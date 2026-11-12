---
name: labels
description: Flag Cold Mails plus Waiting Reply, Need Attention on archived threads, and invoices left in the inbox.
---

# Label sanity

Use on a thread export when checking labels after a pass.

```
python -m clair_toolkit labels THREADS.json
```

`flags` is empty when nothing breaks. Rules:

- `cold_and_waiting` — Label_12 Cold Mails together with Label_9 Waiting Reply
- `need_attention_archived` — Label_4 Need Attention and no INBOX
- `invoice_not_archived` — Label_1 Fatura Irsaliye still in INBOX

Names (`Cold Mails`, `Waiting Reply`) count the same as the ids. This command only reports.
