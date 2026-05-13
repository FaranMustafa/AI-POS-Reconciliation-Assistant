# Sample reconciliation data

Six CSV files for two business days (2026-05-01 and 2026-05-02) designed to
exercise most of the reconciliation engine's rules. Upload them together in
one run from the dashboard ("New reconciliation run" → primary file +
"Add more sources to this run") so cross-source checks fire.

## Files

| File | Source type to pick in UI | Rows |
| --- | --- | --- |
| `pos.csv` | POS daily | 2 daily closes |
| `bank.csv` | Card/bank | 3 deposits |
| `lottery.csv` | Lottery settlement | 2 settlements |
| `fuel.csv` | Fuel invoice | 2 invoices with `Received Gallons` / `Expected Amount` |
| `woocommerce.csv` | WooCommerce | 2 completed orders + 1 pending |
| `expenses.csv` | Expense | 3 bills (two intentionally duplicated) |

## Exceptions you should see after uploading all six

1. **Settlement gap** — 2026-05-01: POS card sales $1,290.10 vs bank deposit
   $1,280.10 (short by $10.00).
2. **Missing entry (orphan deposit)** — 2026-05-03 has a $500.00 card deposit
   with no POS close on that date.
3. **Unresolved suspended sale** — 2026-05-01 has $15.00 in suspended sales.
4. **Total mismatch (lottery)** — 2026-05-01 POS lottery net $88.25 vs lottery
   settlement $90.25 (differs by $2.00).
5. **Total mismatch (fuel gallons)** — 2026-05-01 invoice FUEL-7001 billed
   1,200.000 gallons but received 1,188.500 (off by 11.500).
6. **Suspicious total (fuel amount)** — 2026-05-02 invoice FUEL-7002 amount
   $2,937.00 vs expected $2,900.00 (off by $37.00).
7. **Missing entry (WooCommerce vs POS)** — 2026-05-01 and 2026-05-02
   WooCommerce orders have no matching POS online sales line.
8. **Duplicate entry** — BILL-100 and BILL-101 share external reference
   `EXT-77` for Shell Oil.

Rows that should **not** trigger anything:

- 2026-05-02 close-1002 card $980.50 ↔ deposit batch-9002 $980.50 (matched).
- 2026-05-02 lottery POS $52.40 ↔ settlement LOT-4402 $52.40 (matched).
- WooCommerce order 7783 — status `pending` is ignored by the importer.
- BILL-200 (Acme Supplies $128.00) — unique payee/date/amount.

## Adapt to your own data

Each importer expects the column names shown in the file headers. Extra
columns are ignored. To trigger the fuel-variance rule on your own invoices,
add `Received Gallons` (compares against billed gallons) and/or
`Expected Amount` (compares against billed amount). Both columns are
optional.
