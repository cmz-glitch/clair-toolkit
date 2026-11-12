---
name: handoff-rule
description: Silent handoff. Name the owner and the facts. Do not tell Milou, and do not describe the owner bot's next step.
---

# Handoff rule

Hard rule (Clair t532u). A handoff is silent.

Do not notify Milou that mail was handed off. No chat line, no emoji, no "handed to Vega" note.

Do not describe what the owner bot will do. No "please draft", no "you should", no next-step plan. The owner bot already has its own rules.

Use `python -m clair_toolkit handoff CLASSIFIED.json`. If `handoff` is null, there is nothing to send.

The message shape is fixed:

```
Rule: prospect/cold replies -> Catalina (Clair routing; silent handoff t532u)
From: Ada <ada@prospect.example>
Date: 2026-11-11 12:03 Dubai
Thread: thread-c
Msg: m-c
Ask: introduction — Send a catalogue
Labels: Label_13
Sent: no
```

The first line cites the rule that picked the owner. The other lines are facts only: who wrote, when (Dubai), which thread and message, what they asked, which labels are set, and whether we already sent something.

Vega takes supplier mail, invoices, delivery, goods reception, and payment confirmation. Catalina takes prospect and cold replies, declines, bounces, and auto-replies. Christina takes staff, HR, SGK, SSK, and salary. Clair keeps operational mail and daily confirmed-customer mail, so those do not produce a handoff. Anything else is UNKNOWN: ask the owner in the normal question path. That question is not a handoff notice. Notifications are archived, not handed off.
