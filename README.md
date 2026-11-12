# clair-toolkit

Deterministic helpers for Clair (`operations@entegrepack.com`). One command prints one compact JSON line, so repeat mail work is not reasoned out again. Gmail stays in the connector. These tools only read the JSON, HTML, PDF, and state files you pass.

Queue files on the mailbox host: `/home/box/agent-data/queues/<bot>.md`. Invoice PDFs use `vega_invoices/YYYY-MM-DD_SUPPLIER_INVOICENO.pdf`.

```
pip install -r requirements.txt
python -m clair_toolkit <tool> ...
```

- `efatura` — parse a Turkish e-fatura HTML or PDF into supplier, VKN, amounts, line items, the PDF filename, and a Vega queue line. `python -m clair_toolkit efatura FILE [--thread ID] [--at "YYYY-MM-DD HH:MM"]`
- `queue` — append, mark done, list open items, or chase open items older than N hours. `python -m clair_toolkit queue append|done|list|chase FILE ...`
- `cycle` — check or mark handled threads and record a no-followup, leaving every other key in cycle_state.json as it was. `python -m clair_toolkit cycle is-handled|mark-handled|add-no-followup FILE ...`
- `gate` — return SAFE_TO_REPLY or BLOCK for a thread, and whether the last message is ours. `python -m clair_toolkit gate FILE --ours EMAIL [--days 7]`
- `sent-dup` — flag an earlier Sent message to the same address or company domain. `python -m clair_toolkit sent-dup FILE --to EMAIL [--subject S] [--keyword K]`
- `classify` — label a message invoice, bounce, auto-reply, cold-reply, HR-SGK, notification, or business, with the owner and the labels to add or remove. `python -m clair_toolkit classify FILE [--ours EMAIL]`
- `bounce` — return the failed address, SMTP code, and reason (over quota, no such user, domain not found). `python -m clair_toolkit bounce FILE`
- `lang` — detect TR, EN, FR, AR, or ZH. `python -m clair_toolkit lang --text "..."` or `lang FILE`
- `lint` — PASS or FAIL a draft email or WhatsApp (greeting, signature, language, PS, length, deny-list). `python -m clair_toolkit lint --channel email|whatsapp --thread-lang XX --text-file FILE`
- `dedupe` — match a cold-outreach address against a contacted-email list by address and by domain. `python -m clair_toolkit dedupe FILE --email EMAIL`
- `labels` — flag Cold Mails together with Waiting Reply, Need Attention on an archived thread, or an invoice still in the inbox. `python -m clair_toolkit labels FILE`
- `cleanup` — for each inbox thread, KEEP or ARCHIVE with a reason, one list of ids to archive, and label fixes. It never deletes or moves mail. `python -m clair_toolkit cleanup FILE --state cycle_state.json --ours EMAIL [--queue FILE]`
- `handoff` — name the owner bot and a silent handoff note (rule line, then facts). `python -m clair_toolkit handoff CLASSIFIED.json`

Skill notes for each command are in `skills/`. `skills/handoff-rule/SKILL.md` is the silent-handoff rule.
