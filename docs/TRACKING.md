# AI POS Reconciliation Assistant Tracking

## Current Status

- Phase: MVP feature complete for ingestion and review; production hardening remains
- Workspace state: Django project with CSV/XLSX/pasted-text pipeline, queue-ready run processing, persistence, exports, multi-source runs, and review workspace
- Primary plan: `docs/superpowers/plans/2026-05-12-ai-pos-reconciliation-assistant.md`
- Product scope: MVP for small retailers and accountants reconciling POS, cash, card, fuel, lottery, expenses, invoices, and WooCommerce exports
- Test coverage: 44 Django tests + standalone reconciliation tests all green

## Milestones

| ID | Milestone | Status | Exit Criteria |
| --- | --- | --- | --- |
| M0 | Project scaffold | Done | Django app boots locally, test runner works, dev dependency install succeeds |
| M1 | Upload and parsing foundation | Done | CSV/XLSX/pasted-text importers (POS, card/bank, WooCommerce, fuel, lottery, expense) normalize into canonical transactions |
| M2 | Reconciliation engine | Done | Rules detect settlement gaps, missing/orphan deposits, duplicate entries (incl. cross-source), suspended sales, lottery mismatches, WooCommerce/POS mismatches, fuel invoice variances |
| M3 | Review workspace UI | Done | Upload multiple files in one run; run history, severity/category/status filters, issue resolve/dismiss/reopen actions |
| M4 | Persistence and audit trail | Done | Imports, transactions, runs, issues, and audit events stored with tenant scoping; resolve/dismiss writes audit events |
| M5 | Export and handoff | Done | Issues CSV, accounting-adjustment CSV, and PDF-ready summary all wired into the run detail page |
| M6 | Production readiness | In progress | Auth, tenant isolation, and queue-ready run processing in place; validation, logging, hardening remain |

## Sub-Tasks

| ID | Task | Owner | Status | Depends On |
| --- | --- | --- | --- | --- |
| T01 | Initialize Django project, dependency manifests, and dashboard shell | Codex | Done | None |
| T02 | Define domain models for imports, transactions, tenders, settlements, invoices, issues | Codex | Done | T01 |
| T03 | Build CSV import adapters for POS daily reports and card/bank reports | Codex | Done | T02 |
| T04 | Build WooCommerce order export adapter | Codex | Done | T02 |
| T05 | Build fuel invoice and lottery settlement adapters using tabular text inputs | Codex | Done | T02 |
| T06 | Build normalization pipeline with payee/vendor cleanup and duplicate keys | Codex | Done | T03, T04, T05 |
| T07 | Implement first reconciliation rules and severity sorting | Codex | Done | T06 |
| T08 | Create upload, mapping, and reconciliation run UI | Codex | Done | T03, T07 |
| T09 | Create exception review UI with filters and resolution actions | Codex | Done | T07, T08 |
| T10 | Add database persistence and audit events | Codex | Done | T02, T09 |
| T11 | Add exports for exception reports and accounting adjustments | Codex | Done | T09, T10 |
| T12 | Add auth, tenant boundaries, and production hardening | Codex | In progress | T10 |
| T13 | Expense CSV importer and engine duplicate detection across sources | Codex | Done | T03, T07 |
| T14 | WooCommerce vs POS, fuel invoice variance, and missing/orphan settlement rules | Codex | Done | T07 |
| T15 | Multi-file upload + cross-source run aggregation | Codex | Done | T08, T14 |
| T16 | Accounting adjustment CSV export and PDF-ready summary | Codex | Done | T11 |
| T17 | Run history list page and severity/category/status filters on run detail | Codex | Done | T09 |
| T18 | Issue resolve/dismiss/reopen endpoint with audit events | Codex | Done | T09, T10 |
| T19 | XLSX and pasted-text ingestion (openpyxl + tabular text) | Codex | Done | T13 |
| T20 | Async run processing via Celery/Redis-ready service boundary | Codex | Done | T15 |

## Build Log

| Date | Update |
| --- | --- |
| 2026-05-12 | Switched stack to Django/Python, added core dataclasses, CSV importers, payee normalization, deterministic reconciliation engine, standard-library tests, Django project shell, dashboard route, requirements, and README. |
| 2026-05-12 | Installed dependencies in `.venv`; verified `.venv/bin/python manage.py check`, `.venv/bin/python -m unittest discover -s reconciliation/tests`, and `.venv/bin/python -m ruff check .`. |
| 2026-05-12 | Added persisted import, transaction, reconciliation run, issue, and audit event models with admin registrations and initial migration. Verified `.venv/bin/python manage.py test`, `.venv/bin/python -m unittest discover -s reconciliation/tests`, and `.venv/bin/python -m ruff check .`. |
| 2026-05-12 | Added CSV upload workflow, source type selection, import-to-transaction persistence, reconciliation run creation, issue persistence, and run detail exception table. Verified `.venv/bin/python manage.py test`, `.venv/bin/python manage.py makemigrations --check --dry-run`, `.venv/bin/python -m unittest discover -s reconciliation/tests`, and `.venv/bin/python -m ruff check .`. |
| 2026-05-12 | Added issue CSV export formatter, run issue export route, and run detail export link. Verified `.venv/bin/python manage.py test`, `.venv/bin/python -m unittest discover -s reconciliation/tests`, `.venv/bin/python manage.py makemigrations --check --dry-run`, and `.venv/bin/python -m ruff check .`. |
| 2026-05-12 | Added environment-driven settings for `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, and `DATABASE_URL`, plus `.env.example` and deployment checklist. Verified `.venv/bin/python manage.py test`, `.venv/bin/python -m unittest discover -s reconciliation/tests`, `.venv/bin/python manage.py makemigrations --check --dry-run`, `.venv/bin/python manage.py check`, and `.venv/bin/python -m ruff check .`. |
| 2026-05-12 | Added login-required dashboard access, tenant and membership models, tenant-scoped imports/runs/audit events, and tenant-limited run detail/export access. Verified `.venv/bin/python manage.py test`, `.venv/bin/python -m unittest discover -s reconciliation/tests`, `.venv/bin/python manage.py makemigrations --check --dry-run`, and `.venv/bin/python -m ruff check .`; applied local migration with `.venv/bin/python manage.py migrate`. |
| 2026-05-12 | Added expense CSV importer (`parse_expense_report`), wired EXPENSE source type into `dashboard.services.IMPORTERS`, and covered with importer tests. |
| 2026-05-12 | Expanded engine with WooCommerce-vs-POS online sales check, fuel invoice gallons/amount variance check, missing/orphan card-settlement check, and cross-source expense duplicate detection. Added six new engine tests. |
| 2026-05-12 | Added multi-file upload workflow (`process_uploaded_run`) so one reconciliation run can ingest multiple sources and trigger cross-source checks; updated index template with "Add more sources" disclosure. |
| 2026-05-12 | Added accounting adjustment CSV export (`issues_to_accounting_adjustment_csv`) mapping issue categories to suggested accounts, plus a print/PDF-ready run summary template at `/runs/<id>/summary` with browser-print styling. |
| 2026-05-12 | Added run history page at `/runs/`, severity/category/status filters on run detail, severity badge pills, and resolve/dismiss/reopen issue status endpoint that emits `ISSUE_RESOLVED` / `ISSUE_DISMISSED` audit events. Verified with `python3 manage.py test` (44 passing) and `python3 -m unittest discover -s reconciliation/tests` (23 passing). |
| 2026-05-12 | Extended `parse_fuel_invoice_report` to read optional `Received Gallons` and `Expected Amount` columns so the fuel-variance engine rule can fire from CSV inputs. Added a `sample-data/` folder with six end-to-end CSVs (pos, bank, lottery, fuel, woocommerce, expenses) covering two business days and a README that enumerates the nine exceptions to expect. Simulated run produces 9/9 expected issues. Tests: 25 standalone + 45 Django, all green. |
| 2026-05-13 | Added XLSX upload handling via `openpyxl`, tab-delimited pasted-text parsing, and dashboard pasted text controls. Targeted tests verify XLSX POS uploads create runs and pasted tabular text normalizes through the same importer path. |
| 2026-05-13 | Started T20 async run processing slice: separating run creation from reconciliation execution so Celery/Redis can call the same service path. |
| 2026-05-13 | Completed T20 queue-ready processing boundary: uploads can create a pending run, `process_pending_run(run_id)` executes reconciliation and persists issues, and the dashboard exposes a queued processing option for later Celery wiring. |

## Risks

| Risk | Mitigation |
| --- | --- |
| POS exports vary widely by vendor | Start with configurable column mapping and save mappings per source |
| PDF invoices are messy | MVP accepts CSV/XLSX or copied tabular text first; OCR comes after validated demand |
| Accounting edge cases can explode scope | Encode rules as small, named checks with fixtures and issue explanations |
| Users need trust in AI output | Keep deterministic reconciliation first; use AI only for mapping suggestions and issue explanations |

## Weekly Execution Rhythm

1. Pick the next unchecked task from the implementation plan.
2. Write or update fixtures first.
3. Add the failing unit or integration test.
4. Implement the smallest passing slice.
5. Run tests and update this tracker.
6. Commit with a task-specific message.
