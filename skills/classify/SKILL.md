---
name: classify
description: Rule-only label for one message, plus the owner bot and the Gmail label changes.
---

# Classify

Use on each new message before routing. No model call.

```
python -m clair_toolkit classify MESSAGE.json [--ours ops@entegrepack.com]
```

`category` is `invoice`, `bounce`, `auto-reply`, `cold-reply`, `HR-SGK`, `notification`, or `business`. `owner` is the suggested bot. `labels_add` and `labels_remove` use the real ids (`Label_1` Fatura Irsaliye, `Label_4` Need Attention, `Label_9` Waiting Reply, `Label_12` Cold Mails, `Label_13` Ongoing Prospection). `archive: true` means drop INBOX. `action` is `archive`, `handoff`, `thank_you`, `check_sent`, `ask_owner`, or `none`. `bounce` is filled for bounces. Pass the JSON to `handoff`.

Invoices, bounces, auto-replies, and notifications archive. A cold reply drops Cold Mails and adds Ongoing Prospection. A reply on a Waiting Reply thread that Clair still owns is `thank_you`.
