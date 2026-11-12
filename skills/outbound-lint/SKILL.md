---
name: outbound-lint
description: PASS or FAIL a draft email or WhatsApp before send.
---

# Outbound lint

Open before any email or WhatsApp draft is handed to a send owner. Run `gate` separately for closed threads.

```
python -m clair_toolkit lint --channel email|whatsapp --thread-lang TR --text-file DRAFT [--follow-up] [--first-of-day] [--deny "B name"]
```

`verdict` is `PASS` or `FAIL`. Reasons use a class prefix:

- `G` greeting is Hello, Hi, or Merhaba. First WhatsApp of the day in Turkish must be Merhaba.
- `I` email signature includes a phone number. WhatsApp has no signature.
- `F` draft language matches `--thread-lang`. Missing thread language fails.
- `PS` no postscript.
- `LEN` 3 to 5 sentences, or 2 with `--follow-up`.
- `C` owner location (default deny: dubai).
- `B` other supplier or a PO/CO number in the body (default deny: jayden).

Any FAIL means do not send. The default deny list is `clair_toolkit/data/deny_list.txt`. `--deny` adds a term. `--deny-file` replaces the default list.
