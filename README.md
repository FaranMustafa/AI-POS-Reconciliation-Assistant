# AI POS Reconciliation Assistant

Django-first MVP for reconciling POS daily reports, card and bank deposits, WooCommerce orders, fuel invoices, lottery settlements, expenses, and accounting handoff files.

## Current Build

- Pure Python CSV importers for POS, card/bank, WooCommerce, fuel invoice, lottery settlement, and bookkeeping expense files
- Payee normalization and duplicate keys
- Deterministic reconciliation rules: card settlement gaps, missing/orphan card deposits, duplicate entries (incl. cross-source), unresolved suspended sales, lottery mismatches, WooCommerce vs POS online sales, and fuel invoice gallons/amount variances
- Multi-file upload: ingest several source files into one reconciliation run so cross-source rules can fire
- Django dashboard with run history, severity/category/status filters, and resolve/dismiss/reopen actions (with audit events)
- Exports: issues CSV, accounting-adjustment CSV (journal-entry oriented), and a print/PDF-ready run summary page

## Local Commands

```bash
python3 -m unittest discover -s reconciliation/tests   # 23 standalone tests
python3 -m pip install -r requirements-dev.txt
python3 manage.py migrate
python3 manage.py test                                 # 44 Django tests
python3 manage.py runserver
```

