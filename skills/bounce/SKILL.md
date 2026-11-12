---
name: bounce
description: Read a bounce or DSN and return the failed address and the reason.
---

# Bounce

Use on a mailer-daemon message, or when classify says `bounce`.

```
python -m clair_toolkit bounce FILE
```

FILE is raw DSN text or a message JSON. Read `failed_address`, `smtp_code`, and `reason`: `over_quota` (552, mailbox full), `no_such_user` (550), `domain_not_found`, `rejected`, or `unknown`. `detail` is a short clip of the source. Hand the address and reason to Catalina. Do not follow up on the bounced thread.
