---
name: dedupe
description: Skip a cold-outreach address already contacted, by address or by domain.
---

# Cold-outreach dedupe

Use before a first-touch email. The list is one address per line.

```
python -m clair_toolkit dedupe CONTACTS.txt --email PERSON@COMPANY
```

`new` is safe to contact. `skip` is already contacted. `via: address` is the same mailbox. `via: domain` is another mailbox at the same company. Public hosts (gmail, outlook, yahoo, icloud, and the rest of the freemail set) match only on the full address. `hit: false` means every candidate is new.
