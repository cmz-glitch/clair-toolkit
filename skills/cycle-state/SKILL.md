---
name: cycle-state
description: Check and update handled threads and no-followup rows in cycle_state.json.
---

# Cycle state

Use before acting on a thread, and after the action is done. Skip ids already in `handled_thread_ids`.

```
python -m clair_toolkit cycle is-handled FILE --thread ID [--message ID]
python -m clair_toolkit cycle mark-handled FILE --thread ID --note "TEXT" [--message ID]
python -m clair_toolkit cycle add-no-followup FILE --company C --email E --domain D --thread ID --reason R --date YYYY-MM-DD
```

`is-handled` returns `handled` and `via` (`thread` or `message`). `no_followup: true` means the thread is on the do-not-chase list; that alone is not "handled". `mark-handled` inserts the thread once and keeps the first note. A message id is added once. `add-no-followup` skips a row that already has the same email or thread id (`added: false`). `last_cycle` and every other key stay untouched.
