---
name: cleanup
description: Plan which inbox threads to keep or archive. It does not move or delete mail.
---

# Inbox cleanup

Use when operations@ should hold only mail that still needs a reply. Input is an INBOX export plus cycle_state.

```
python -m clair_toolkit cleanup INBOX.json --state cycle_state.json --ours ops@entegrepack.com [--queue /home/box/agent-data/queues/clair.md]
```

Each `plan` row is `KEEP` or `ARCHIVE` with a reason. `archive_ids` is the batch to archive. `label_fixes` lists labels to remove.

KEEP only `need_attention_unanswered` (Label_4, last message inbound, not handled) and `open_queue` (the thread id is on an open queue line).

ARCHIVE covers handled threads, threads we already answered, notifications, filed invoices (Label_1), bounces, auto-replies, Waiting Reply, and Cold Mails. Waiting Reply and Cold Mails keep those labels and leave the inbox. Need Attention comes off once our reply is the last message (`reply_is_last`). Cold Mails plus Waiting Reply drops Waiting Reply only.

The command writes nothing to Gmail.
