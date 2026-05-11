from decimal import Decimal

from django.test import TestCase

from imports.models import (
    AuditEvent,
    CanonicalTransactionRecord,
    ImportFile,
    ReconciliationIssueRecord,
    ReconciliationRun,
)


class PersistenceModelTests(TestCase):
    def test_import_file_owns_canonical_transactions(self):
        import_file = ImportFile.objects.create(
            source_type=ImportFile.SourceType.POS_DAILY,
            original_filename="pos-daily.csv",
            content_type="text/csv",
            file_size=512,
            status=ImportFile.Status.PROCESSED,
        )

        transaction = CanonicalTransactionRecord.objects.create(
            import_file=import_file,
            source_transaction_id="import-pos:close-1001:cash",
            source_type=ImportFile.SourceType.POS_DAILY,
            business_date="2026-05-01",
            posted_at="2026-05-01T12:00:00Z",
            category=CanonicalTransactionRecord.Category.SALE,
            tender_type=CanonicalTransactionRecord.TenderType.CASH,
            external_ref="close-1001",
            payee_key=None,
            description="POS Cash Sales",
            amount=Decimal("421.55"),
            metadata={"register": "1"},
        )

        self.assertEqual(import_file.transactions.count(), 1)
        self.assertEqual(import_file.transactions.first(), transaction)

    def test_reconciliation_run_owns_issues(self):
        import_file = ImportFile.objects.create(
            source_type=ImportFile.SourceType.CARD_BANK,
            original_filename="card-bank.csv",
            content_type="text/csv",
            file_size=256,
            status=ImportFile.Status.PROCESSED,
        )
        run = ReconciliationRun.objects.create(status=ReconciliationRun.Status.COMPLETED)
        run.import_files.add(import_file)

        issue = ReconciliationIssueRecord.objects.create(
            run=run,
            severity=ReconciliationIssueRecord.Severity.HIGH,
            category=ReconciliationIssueRecord.Category.SETTLEMENT_GAP,
            title="Card settlement does not match POS sales",
            evidence=["POS card sales 1290.10; deposits 1280.10; short by 10.00."],
            recommended_action="Check processor batch timing and missing deposits.",
            related_transaction_ids=["pos-card", "bank-card"],
        )

        self.assertEqual(run.import_files.count(), 1)
        self.assertEqual(run.issues.count(), 1)
        self.assertEqual(run.issues.first(), issue)

    def test_audit_event_records_action_context(self):
        import_file = ImportFile.objects.create(
            source_type=ImportFile.SourceType.FUEL_INVOICE,
            original_filename="fuel.csv",
            content_type="text/csv",
            file_size=128,
            status=ImportFile.Status.RECEIVED,
        )

        audit_event = AuditEvent.objects.create(
            action=AuditEvent.Action.IMPORT_CREATED,
            import_file=import_file,
            actor_label="system",
            metadata={"source_type": ImportFile.SourceType.FUEL_INVOICE},
        )

        self.assertEqual(audit_event.import_file, import_file)
        self.assertEqual(audit_event.action, AuditEvent.Action.IMPORT_CREATED)
        self.assertEqual(audit_event.metadata["source_type"], ImportFile.SourceType.FUEL_INVOICE)

