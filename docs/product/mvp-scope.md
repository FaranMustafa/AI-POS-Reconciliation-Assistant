# MVP Scope

## Target Users

- Independent gas station and convenience store owners
- Bookkeepers handling daily close packs
- Small accounting firms reconciling retail clients
- Back-office staff matching POS, bank, card, fuel, lottery, expense, and e-commerce records

## Primary Job

Given messy operational exports, detect reconciliation exceptions that normally take hours to find manually.

## MVP Inputs

- POS daily sales CSV or XLSX export
- Card processor or bank deposit CSV export
- WooCommerce order CSV export
- Fuel invoice CSV, XLSX, or pasted tabular text
- Lottery settlement CSV, XLSX, or pasted tabular text
- Expense/payee CSV export

## Approved Technical Direction

- Backend: Python and Django
- API layer: Django REST Framework where API endpoints are needed
- Data processing: pure Python first, with Pandas/openpyxl/pdfplumber added for larger Excel and PDF handling
- UI: Django templates, Tailwind CSS, and HTMX for the MVP
- Background processing: Celery and Redis once uploads become long-running
- Database: PostgreSQL in production; SQLite is acceptable for early local development

## MVP Outputs

- Reconciliation run summary
- Exception list with severity, category, evidence, and recommended action
- Duplicate payee/vendor report
- Missing or unmatched settlement report
- Accounting adjustment CSV
- PDF-ready exception summary after the app has an export renderer

## Reconciliation Checks

- Sales total does not match expected cash, card, lottery, fuel, or online settlement totals
- Bank/card deposit is missing for a POS batch
- Deposit exists without matching POS close
- Duplicate payee or vendor entry
- Suspended sale remains unresolved after close
- WooCommerce paid order is missing from POS/accounting sales
- Fuel invoice gallons or amount differs from received inventory or expected payable
- Lottery settlement cash due differs from POS lottery net
- Expense appears twice across POS payout, bill, and bank/card statement

## Out Of Scope For MVP

- Full accounting ledger replacement
- Direct bank/POS API integrations
- OCR for photographed invoices
- Automated payment initiation
- Tax filing
- Inventory forecasting
