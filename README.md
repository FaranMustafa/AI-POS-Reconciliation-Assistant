# AI POS Reconciliation Assistant

Django-first MVP for reconciling POS daily reports, card and bank deposits, WooCommerce orders, fuel invoices, lottery settlements, expenses, and accounting handoff files.

## Current Build

- Pure Python CSV importers for POS, card/bank, WooCommerce, fuel invoice, and lottery settlement files
- Payee normalization and duplicate keys
- Deterministic reconciliation rules for card settlement gaps, duplicate entries, suspended sales, and lottery mismatches
- Django project shell with a dashboard landing screen

## Local Commands

```bash
python3 -m unittest discover -s reconciliation/tests
python3 -m pip install -r requirements-dev.txt
python3 manage.py runserver
```

