# AI POS Reconciliation Assistant Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Django MVP web app that imports retail reconciliation files, normalizes messy operational data, detects mismatches and duplicates, and gives accountants a clear exception workflow.

**Architecture:** Use a Django monolith with pure-Python reconciliation modules, Django views/templates for the review workspace, and Django REST Framework endpoints when the workflow needs API access. Keep financial checks deterministic and fixture-driven; use AI later only for mapping suggestions and plain-English explanations.

**Tech Stack:** Python, Django, Django REST Framework, PostgreSQL, Celery, Redis, Pandas, openpyxl, pdfplumber, Tailwind CSS, HTMX, unittest/pytest, pytest-django.

---

## File Structure

- `manage.py`: Django command entrypoint.
- `config/settings.py`: local Django settings.
- `config/urls.py`: root URL configuration.
- `dashboard/views.py`: dashboard and upload/review screens.
- `templates/dashboard/index.html`: first usable dashboard.
- `reconciliation/types.py`: canonical transaction and issue dataclasses.
- `reconciliation/importers.py`: CSV import adapters for POS, card/bank, WooCommerce, fuel, and lottery.
- `reconciliation/normalization.py`: payee cleanup and duplicate key generation.
- `reconciliation/engine.py`: deterministic reconciliation rules and severity sorting.
- `reconciliation/tests/*.py`: standard-library tests for core behavior.
- `requirements.txt`: runtime dependencies.
- `requirements-dev.txt`: development and test dependencies.
- `docs/TRACKING.md`: milestone and task state.

## Task 1: Django Project Shell

**Files:**
- Create: `manage.py`
- Create: `config/settings.py`
- Create: `config/urls.py`
- Create: `config/asgi.py`
- Create: `config/wsgi.py`
- Create: `dashboard/apps.py`
- Create: `dashboard/urls.py`
- Create: `dashboard/views.py`
- Create: `templates/dashboard/index.html`
- Create: `requirements.txt`
- Create: `requirements-dev.txt`
- Create: `README.md`

- [x] **Step 1: Add Django dependency manifests**

Runtime dependencies include Django, Django REST Framework, Pandas, openpyxl, pdfplumber, psycopg, celery, redis, and python-decouple.

- [x] **Step 2: Add Django project files**

The project uses `config.settings`, `config.urls`, and a `dashboard` app.

- [x] **Step 3: Add first dashboard template**

The first screen exposes a reconciliation-run shell with supported input types and upload placeholder.

- [x] **Step 4: Install dependencies**

Run:

```bash
python3 -m pip install -r requirements-dev.txt
```

Expected: dependencies install successfully.

- [x] **Step 5: Verify Django boot**

Run:

```bash
python3 manage.py check
```

Expected: Django system check reports no issues.

## Task 2: Canonical Domain Types

**Files:**
- Create: `reconciliation/types.py`
- Test: `reconciliation/tests/test_reconciliation_engine.py`

- [x] **Step 1: Write failing tests using `CanonicalTransaction`**

Tests import `CanonicalTransaction` and construct real records for reconciliation.

- [x] **Step 2: Verify failing test**

Run:

```bash
python3 -m unittest discover -s reconciliation/tests
```

Expected: fails because `reconciliation.types` does not exist.

- [x] **Step 3: Implement dataclasses**

`CanonicalTransaction` and `ReconciliationIssue` are frozen dataclasses with explicit fields.

- [x] **Step 4: Verify passing tests**

Run:

```bash
python3 -m unittest discover -s reconciliation/tests
```

Expected: tests pass after related modules are implemented.

## Task 3: CSV Import Adapters

**Files:**
- Create: `reconciliation/importers.py`
- Test: `reconciliation/tests/test_importers.py`

- [x] **Step 1: Write failing importer tests**

Tests cover POS daily reports, card/bank deposits, WooCommerce orders, fuel invoices, and lottery settlements.

- [x] **Step 2: Implement importers**

Functions:

```python
parse_pos_daily_report(content, source_import_id)
parse_card_bank_report(content, source_import_id)
parse_woocommerce_orders(content, source_import_id)
parse_fuel_invoice_report(content, source_import_id)
parse_lottery_settlement_report(content, source_import_id)
```

- [x] **Step 3: Verify importers**

Run:

```bash
python3 -m unittest discover -s reconciliation/tests
```

Expected: importer tests pass.

## Task 4: Normalization

**Files:**
- Create: `reconciliation/normalization.py`
- Test: `reconciliation/tests/test_normalization.py`

- [x] **Step 1: Write failing normalization tests**

Tests cover common vendor suffix cleanup and duplicate key behavior.

- [x] **Step 2: Implement normalization**

Functions:

```python
normalize_payee(value)
create_duplicate_key(business_date, amount, payee_key, external_ref)
```

- [x] **Step 3: Verify normalization**

Run:

```bash
python3 -m unittest discover -s reconciliation/tests
```

Expected: normalization tests pass.

## Task 5: Reconciliation Engine

**Files:**
- Create: `reconciliation/engine.py`
- Test: `reconciliation/tests/test_reconciliation_engine.py`

- [x] **Step 1: Write failing rule tests**

Tests cover card settlement gaps, duplicate payee entries, unresolved suspended sales, and lottery settlement mismatches.

- [x] **Step 2: Implement engine**

`run_reconciliation(run_id, transactions)` calls deterministic checks and returns sorted issues.

- [x] **Step 3: Verify engine**

Run:

```bash
python3 -m unittest discover -s reconciliation/tests
```

Expected: all 12 current tests pass.

## Task 6: Persistence Models

**Files:**
- Create: `imports/models.py`
- Create: `imports/admin.py`
- Create: `imports/migrations/0001_initial.py`
- Modify: `config/settings.py`
- Test: `imports/tests/test_models.py`

- [x] **Step 1: Add Django app for persisted imports and runs**

Create models for `ImportFile`, `CanonicalTransactionRecord`, `ReconciliationRun`, `ReconciliationIssueRecord`, and `AuditEvent`.

- [x] **Step 2: Add model tests**

Test that an import can own transactions, a run can own issues, and an audit event records the action.

- [x] **Step 3: Run migrations and tests**

Run:

```bash
python3 manage.py makemigrations
python3 manage.py test
```

Expected: migrations are created and tests pass.

## Task 7: Upload And Run Workflow

**Files:**
- Modify: `dashboard/views.py`
- Modify: `dashboard/urls.py`
- Modify: `templates/dashboard/index.html`
- Create: `templates/dashboard/run_detail.html`
- Test: `dashboard/tests/test_views.py`

- [ ] **Step 1: Add upload form tests**

Test file upload, source type selection, import parsing, reconciliation run creation, and redirect to run detail.

- [ ] **Step 2: Implement upload view**

Accept CSV files, route to the selected importer, persist transactions, run reconciliation, and show issues.

- [ ] **Step 3: Verify web flow**

Run:

```bash
python3 manage.py test dashboard
```

Expected: upload and run detail tests pass.

## Task 8: Export Handoff

**Files:**
- Create: `reconciliation/exports.py`
- Modify: `dashboard/views.py`
- Test: `reconciliation/tests/test_exports.py`

- [ ] **Step 1: Add CSV export tests**

Headers:

```csv
Severity,Category,Title,Evidence,Recommended Action,Related Transactions
```

- [ ] **Step 2: Implement export**

Escape commas, quotes, and newlines correctly. Join evidence with ` | `.

- [ ] **Step 3: Verify export**

Run:

```bash
python3 -m unittest reconciliation.tests.test_exports
```

Expected: export tests pass.

## Task 9: Production Readiness

**Files:**
- Create: `.env.example`
- Create: `docs/operations/deployment-checklist.md`
- Modify: `config/settings.py`

- [ ] **Step 1: Add environment configuration**

Use `python-decouple` for `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, and `DATABASE_URL`.

- [ ] **Step 2: Add production checklist**

Cover database migration, static files, object storage, auth, backups, log retention, and smoke tests.

- [ ] **Step 3: Final verification**

Run:

```bash
python3 -m unittest discover -s reconciliation/tests
python3 manage.py check
```

Expected: tests and Django checks pass.

## Self-Review

- Spec coverage: The plan covers Django scaffolding, file import, normalization, reconciliation checks, review UI, persistence, export, and production readiness.
- Scope control: Direct POS/bank API integrations, OCR, and full accounting ledger replacement remain outside the MVP.
- Placeholder scan: No task uses placeholder wording as an implementation substitute.
- Type consistency: `CanonicalTransaction` and `ReconciliationIssue` are the domain objects used by importers, normalization, and reconciliation.
