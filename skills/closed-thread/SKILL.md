---
name: closed-thread
description: Decide SAFE_TO_REPLY or BLOCK before any reply on an existing thread.
---

# Closed-thread gate

Open before a draft or a send on a thread that already exists.

```
python -m clair_toolkit gate THREAD.json --ours ops@entegrepack.com [--days 7] [--now ISO]
```

`verdict` is `SAFE_TO_REPLY` or `BLOCK`. `reason` is `open`, `finalized`, `archived`, `already_replied`, `stale`, or `empty`. `waiting_reply: true` means the last message is ours (Waiting Reply). Archived means the thread labels have no INBOX. Stale means the last inbound is older than N days (default 7). A block here means do not reply unless the owner explicitly said yes for this send.
