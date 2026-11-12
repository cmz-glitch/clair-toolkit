---
name: handoff
description: Turn a classify result into the owner bot and a silent handoff note.
---

# Handoff

Use after `classify`, when the message belongs to another bot. Read `skills/handoff-rule/SKILL.md` first. The handoff is silent.

```
python -m clair_toolkit handoff CLASSIFIED.json
```

`owner` is Vega, Catalina, Christina, Clair, NONE, or UNKNOWN.

- Vega — supplier, invoice, delivery, goods reception, payment confirmation
- Catalina — prospect or cold replies, declines, bounces, auto-replies
- Christina — staff, HR, SGK, SSK, salary
- Clair — operational and daily confirmed-customer mail (`handoff` is null; she keeps it)
- NONE — notification, archive it
- UNKNOWN — `ask_owner: true` and `handoff: null`

When `handoff` is set, send that text to the owner bot only. Line 1 is the rule, including `silent handoff t532u`. The next lines are From, Date in Dubai, Thread, Msg, Ask, Labels, Sent. Do not add a sentence about what that bot will do.
