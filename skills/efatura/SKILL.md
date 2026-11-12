---
name: efatura
description: Parse a Turkish e-fatura HTML or PDF into fields, a PDF filename, and a Vega queue line.
---

# e-fatura

Use when a supplier e-invoice HTML (GİB/EVA viewer) or PDF is saved, before naming the file or queueing Vega.

```
python -m clair_toolkit efatura FILE [--thread THREAD_ID] [--at "YYYY-MM-DD HH:MM"]
```

Read `supplier`, `vkn`, `invoice_no`, `date`, `net`, `kdv`, `total`, `currency`, `due_date`, `lines`. Money is a decimal string. `filename` is `YYYY-MM-DD_SUPPLIER_INVOICENO.pdf` (legal words and a trailing trade word such as KARGO are dropped, then at most three tokens). `queue_line` is the checkbox line to append. The supplier VKN is the one before SAYIN.

`{"ok":false,"error":"edm_shell"}` means the file is only the EDM viewer frame. Pass the inner HTML or the PDF.
