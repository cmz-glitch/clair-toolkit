---
name: queue
description: Append, close, list, and chase items in a bot queue markdown file.
---

# Queue

Use instead of hand-editing `/home/box/agent-data/queues/<bot>.md`.

```
python -m clair_toolkit queue append FILE --from BOT --task "TEXT" --ref REF [--at "YYYY-MM-DD HH:MM"]
python -m clair_toolkit queue done FILE --ref REF
python -m clair_toolkit queue list FILE
python -m clair_toolkit queue chase FILE --hours N [--bot NAME] [--now "YYYY-MM-DD HH:MM"]
```

Lines are `- [ ] YYYY-MM-DD HH:MM | from | task | ref` (done is `- [x]`). Append writes that line and is a no-op when the same ref is already open (`appended: false`). `done` flips matching open lines and reports `updated` and `already_done`. `list` returns `open`. `chase` returns open items older than N hours. `--bot` keeps items whose from-field contains that name. Timestamps are Dubai wall time. Other lines in the file stay as they are.
