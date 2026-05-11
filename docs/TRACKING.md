# AI POS Reconciliation Assistant Tracking

## Current Status

- Phase: Initial build
- Workspace state: Django project shell created; not a git repository
- Primary plan: `docs/superpowers/plans/2026-05-12-ai-pos-reconciliation-assistant.md`
- Product scope: MVP for small retailers and accountants reconciling POS, cash, card, fuel, lottery, expenses, invoices, and WooCommerce exports

## Milestones

| ID | Milestone | Status | Exit Criteria |
| --- | --- | --- | --- |
| M0 | Project scaffold | Done | Django app boots locally, test runner works, dev dependency install succeeds |
| M1 | Upload and parsing foundation | In progress | CSV/XLSX/PDF-like text imports normalize into canonical transactions |
| M2 | Reconciliation engine | In progress | Rules detect missing sales, duplicates, totals mismatches, settlement gaps |
| M3 | Review workspace UI | Not started | User can upload files, inspect exceptions, filter issues, mark resolved |
| M4 | Persistence and audit trail | In progress | Imports, runs, issues, decisions, and exports are stored and auditable |
| M5 | Export and handoff | Not started | User can export exception reports and accounting-ready adjustment CSVs |
| M6 | Production readiness | Not started | Auth, tenant isolation, validation, logging, deployment checklist complete |

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
| T08 | Create upload, mapping, and reconciliation run UI | Unassigned | Not started | T03, T07 |
| T09 | Create exception review UI with filters and resolution actions | Unassigned | Not started | T07, T08 |
| T10 | Add database persistence and audit events | Codex | In progress | T02, T09 |
| T11 | Add exports for exception reports and accounting adjustments | Unassigned | Not started | T09, T10 |
| T12 | Add auth, tenant boundaries, and production hardening | Unassigned | Not started | T10 |

## Build Log

| Date | Update |
| --- | --- |
| 2026-05-12 | Switched stack to Django/Python, added core dataclasses, CSV importers, payee normalization, deterministic reconciliation engine, standard-library tests, Django project shell, dashboard route, requirements, and README. |
| 2026-05-12 | Installed dependencies in `.venv`; verified `.venv/bin/python manage.py check`, `.venv/bin/python -m unittest discover -s reconciliation/tests`, and `.venv/bin/python -m ruff check .`. |
| 2026-05-12 | Added persisted import, transaction, reconciliation run, issue, and audit event models with admin registrations and initial migration. Verified `.venv/bin/python manage.py test`, `.venv/bin/python -m unittest discover -s reconciliation/tests`, and `.venv/bin/python -m ruff check .`. |

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
