---
name: milou-card
description: Build every question card to Milou with milou-card. Never send a hand-made card.
---

CARD RULE (Milou 12 Nov 2026, HARD): every question card to Milou must be built with the shared script, never by hand:

milou-card "<one question?>" "<recommended option>" "<option 2>" "<option 3>" "<option 4>"

Pass its JSON output unchanged as the SendToUser widget. It always sets the write-in box (allowCustom) and multiSelect on, needs 4 to 6 options, and puts the recommended option first. If it prints BROKEN CARD, fix the card and never send it anyway. To mark option N red, put --danger N before the question. To check a card written by hand: milou-card --lint card.json
Full rules: skill milou-question-card. Save this to your own rules now.
