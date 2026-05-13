from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from openpyxl import Workbook

from imports.models import (
    AuditEvent,
    CanonicalTransactionRecord,
    ImportFile,
    Membership,
    ReconciliationIssueRecord,
    ReconciliationRun,
    Tenant,
)
from dashboard.services import process_pending_run


class UploadWorkflowTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Main Street Fuel")
        self.user = get_user_model().objects.create_user(
            username="owner",
            password="password",
        )
        Membership.objects.create(
            tenant=self.tenant,
            user=self.user,
            role=Membership.Role.OWNER,
        )

    def login(self):
        self.client.force_login(self.user)

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("dashboard:index"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])

    def test_invoice_generator_requires_login(self):
        response = self.client.get(reverse("dashboard:invoice_generator"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])

    def test_invoice_generator_page_renders(self):
        self.login()

        response = self.client.get(reverse("dashboard:invoice_generator"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invoice generator")
        self.assertContains(response, reverse("dashboard:index"))
        self.assertContains(response, reverse("dashboard:run_history"))
        self.assertContains(response, 'name="invoice_type"')
        self.assertContains(response, 'data-invoice-panel="fuel_invoice"')
        self.assertContains(response, 'data-invoice-panel="expense"')
        self.assertContains(response, 'data-invoice-panel="lottery_settlement"')
        self.assertContains(response, "Fuel invoice details")
        self.assertContains(response, "Expense bill details")
        self.assertContains(response, "Lottery settlement details")

    def test_invoice_generator_downloads_parseable_fuel_csv(self):
        self.login()

        response = self.client.post(
            reverse("dashboard:invoice_generator"),
            {
                "invoice_type": "fuel_invoice",
                "invoice_date": "2026-05-01",
                "invoice_number": "FUEL-9001",
                "vendor": "Shell Oil Co. #123",
                "gallons": "1200.000",
                "amount": "3198.75",
                "received_gallons": "1188.500",
                "expected_amount": "3150.00",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertEqual(
            response["Content-Disposition"],
            'attachment; filename="generated-fuel-invoice.csv"',
        )
        self.assertIn(b"Invoice Date,Invoice Number,Vendor,Gallons,Amount", response.content)

    def test_index_displays_upload_form(self):
        self.login()

        response = self.client.get(reverse("dashboard:index"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "New reconciliation run")
        self.assertContains(response, reverse("dashboard:invoice_generator"))
        self.assertContains(response, reverse("dashboard:run_history"))
        self.assertContains(response, 'name="source_type"')
        self.assertContains(response, 'name="source_file"')
        self.assertContains(response, "Expense")
        self.assertContains(response, 'name="multi_source_type"')
        self.assertContains(response, 'name="multi_source_file"')

    def test_upload_pos_csv_creates_import_run_issue_and_redirects(self):
        self.login()

        content = (
            "Business Date,Close ID,Cash Sales,Card Sales,Fuel Sales,Lottery Net,Suspended Sales\n"
            "2026-05-01,close-1001,421.55,1290.10,3200.00,88.25,15.00\n"
        )
        upload = SimpleUploadedFile(
            "pos-daily.csv",
            content.encode("utf-8"),
            content_type="text/csv",
        )

        with self.assertLogs("pos_reconciliation", level="INFO") as captured:
            response = self.client.post(
                reverse("dashboard:index"),
                {"source_type": ImportFile.SourceType.POS_DAILY, "source_file": upload},
            )

        run = ReconciliationRun.objects.get()
        self.assertRedirects(response, reverse("dashboard:run_detail", args=[run.pk]))

        import_file = ImportFile.objects.get()
        self.assertEqual(import_file.tenant, self.tenant)
        self.assertEqual(import_file.status, ImportFile.Status.PROCESSED)
        self.assertEqual(import_file.original_filename, "pos-daily.csv")
        self.assertEqual(import_file.transactions.count(), 5)
        self.assertEqual(CanonicalTransactionRecord.objects.filter(category="adjustment").count(), 1)

        issue = ReconciliationIssueRecord.objects.get(
            category=ReconciliationIssueRecord.Category.UNRESOLVED_SUSPENDED_SALE
        )
        self.assertEqual(run.tenant, self.tenant)
        self.assertEqual(issue.run, run)
        self.assertEqual(issue.category, ReconciliationIssueRecord.Category.UNRESOLVED_SUSPENDED_SALE)
        self.assertIn("Suspended sale", issue.title)

        self.assertEqual(AuditEvent.objects.filter(action=AuditEvent.Action.IMPORT_CREATED).count(), 1)
        self.assertEqual(AuditEvent.objects.filter(action=AuditEvent.Action.IMPORT_PROCESSED).count(), 1)
        self.assertEqual(AuditEvent.objects.filter(action=AuditEvent.Action.RUN_CREATED).count(), 1)
        self.assertTrue(any("import_processed" in message for message in captured.output))
        self.assertTrue(any("run_completed" in message for message in captured.output))

    def test_run_detail_displays_issues(self):
        self.login()

        import_file = ImportFile.objects.create(
            tenant=self.tenant,
            source_type=ImportFile.SourceType.POS_DAILY,
            original_filename="pos-daily.csv",
            content_type="text/csv",
            file_size=128,
            status=ImportFile.Status.PROCESSED,
        )
        run = ReconciliationRun.objects.create(
            tenant=self.tenant,
            status=ReconciliationRun.Status.COMPLETED,
        )
        run.import_files.add(import_file)
        ReconciliationIssueRecord.objects.create(
            run=run,
            severity=ReconciliationIssueRecord.Severity.MEDIUM,
            category=ReconciliationIssueRecord.Category.UNRESOLVED_SUSPENDED_SALE,
            title="Suspended sale remains unresolved after close",
            evidence=["2026-05-01 has suspended sales of 15.00."],
            recommended_action="Resolve the suspended transaction.",
            related_transaction_ids=["txn-1"],
        )

        response = self.client.get(reverse("dashboard:run_detail", args=[run.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Run #")
        self.assertContains(response, "Suspended sale remains unresolved after close")
        self.assertContains(response, "Resolve the suspended transaction.")

    def test_run_issues_export_downloads_csv(self):
        self.login()

        run = ReconciliationRun.objects.create(
            tenant=self.tenant,
            status=ReconciliationRun.Status.COMPLETED,
        )
        ReconciliationIssueRecord.objects.create(
            run=run,
            severity=ReconciliationIssueRecord.Severity.HIGH,
            category=ReconciliationIssueRecord.Category.SETTLEMENT_GAP,
            title="Card settlement does not match POS sales",
            evidence=["POS card sales 1290.10", "Deposits 1280.10"],
            recommended_action="Check processor batch timing.",
            related_transaction_ids=["pos-card", "bank-card"],
        )

        response = self.client.get(reverse("dashboard:run_issues_export", args=[run.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertEqual(
            response["Content-Disposition"],
            'attachment; filename="reconciliation-run-1-issues.csv"',
        )
        self.assertContains(response, "Severity,Category,Title,Evidence,Recommended Action,Related Transactions")
        self.assertContains(response, "settlement_gap")

    def test_multi_file_upload_creates_single_run_with_cross_source_issues(self):
        self.login()

        pos = SimpleUploadedFile(
            "pos.csv",
            (
                "Business Date,Close ID,Cash Sales,Card Sales,Fuel Sales,Lottery Net,Suspended Sales\n"
                "2026-05-01,close-2001,300.00,1290.10,0.00,0.00,0.00\n"
            ).encode("utf-8"),
            content_type="text/csv",
        )
        bank = SimpleUploadedFile(
            "bank.csv",
            (
                "Posted Date,Deposit Ref,Description,Amount\n"
                "2026-05-01,batch-9001,CARD SETTLEMENT,1280.10\n"
            ).encode("utf-8"),
            content_type="text/csv",
        )

        response = self.client.post(
            reverse("dashboard:index"),
            {
                "source_type": ImportFile.SourceType.POS_DAILY,
                "source_file": pos,
                "multi_source_type": [ImportFile.SourceType.CARD_BANK],
                "multi_source_file": [bank],
            },
        )

        run = ReconciliationRun.objects.get()
        self.assertRedirects(response, reverse("dashboard:run_detail", args=[run.pk]))
        self.assertEqual(run.import_files.count(), 2)
        self.assertTrue(
            ReconciliationIssueRecord.objects.filter(
                run=run,
                category=ReconciliationIssueRecord.Category.SETTLEMENT_GAP,
            ).exists()
        )

    def test_upload_xlsx_file_creates_import_run(self):
        self.login()
        workbook = Workbook()
        sheet = workbook.active
        sheet.append(
            [
                "Business Date",
                "Close ID",
                "Cash Sales",
                "Card Sales",
                "Fuel Sales",
                "Lottery Net",
                "Suspended Sales",
            ]
        )
        sheet.append(["2026-05-01", "close-3001", 100, 200, 300, 10, 0])
        buffer = __import__("io").BytesIO()
        workbook.save(buffer)
        buffer.seek(0)
        upload = SimpleUploadedFile(
            "pos-daily.xlsx",
            buffer.read(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        response = self.client.post(
            reverse("dashboard:index"),
            {"source_type": ImportFile.SourceType.POS_DAILY, "source_file": upload},
        )

        run = ReconciliationRun.objects.get()
        self.assertRedirects(response, reverse("dashboard:run_detail", args=[run.pk]))
        self.assertEqual(ImportFile.objects.get().original_filename, "pos-daily.xlsx")
        self.assertEqual(CanonicalTransactionRecord.objects.count(), 4)

    def test_rejects_unsupported_upload_extension(self):
        self.login()
        upload = SimpleUploadedFile(
            "pos-daily.pdf",
            b"%PDF-1.4",
            content_type="application/pdf",
        )

        response = self.client.post(
            reverse("dashboard:index"),
            {"source_type": ImportFile.SourceType.POS_DAILY, "source_file": upload},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Only CSV, XLSX, or pasted tabular text is supported.")
        self.assertEqual(ImportFile.objects.count(), 0)

    def test_rejects_upload_over_size_limit(self):
        self.login()
        upload = SimpleUploadedFile(
            "pos-daily.csv",
            b"x" * (10 * 1024 * 1024 + 1),
            content_type="text/csv",
        )

        response = self.client.post(
            reverse("dashboard:index"),
            {"source_type": ImportFile.SourceType.POS_DAILY, "source_file": upload},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "File is larger than the 10 MB limit.")
        self.assertEqual(ImportFile.objects.count(), 0)

    def test_pasted_tabular_text_creates_import_run(self):
        self.login()
        pasted_content = (
            "Business Date\tClose ID\tCash Sales\tCard Sales\tFuel Sales\tLottery Net\tSuspended Sales\n"
            "2026-05-01\tclose-4001\t100.00\t200.00\t300.00\t10.00\t0.00\n"
        )

        response = self.client.post(
            reverse("dashboard:index"),
            {
                "pasted_source_type": ImportFile.SourceType.POS_DAILY,
                "pasted_content": pasted_content,
            },
        )

        run = ReconciliationRun.objects.get()
        self.assertRedirects(response, reverse("dashboard:run_detail", args=[run.pk]))
        import_file = ImportFile.objects.get()
        self.assertEqual(import_file.original_filename, "pasted-pos_daily.txt")
        self.assertEqual(CanonicalTransactionRecord.objects.count(), 4)

    def test_async_mode_creates_pending_run_then_processes_it(self):
        self.login()
        upload = SimpleUploadedFile(
            "pos-daily.csv",
            (
                "Business Date,Close ID,Cash Sales,Card Sales,Fuel Sales,Lottery Net,Suspended Sales\n"
                "2026-05-01,close-5001,100.00,200.00,0.00,0.00,15.00\n"
            ).encode("utf-8"),
            content_type="text/csv",
        )

        response = self.client.post(
            reverse("dashboard:index"),
            {
                "source_type": ImportFile.SourceType.POS_DAILY,
                "source_file": upload,
                "processing_mode": "queued",
            },
        )

        run = ReconciliationRun.objects.get()
        self.assertRedirects(response, reverse("dashboard:run_detail", args=[run.pk]))
        self.assertEqual(run.status, ReconciliationRun.Status.PENDING)
        self.assertEqual(run.issues.count(), 0)

        process_pending_run(run.id)

        run.refresh_from_db()
        self.assertEqual(run.status, ReconciliationRun.Status.COMPLETED)
        self.assertTrue(
            run.issues.filter(
                category=ReconciliationIssueRecord.Category.UNRESOLVED_SUSPENDED_SALE
            ).exists()
        )

    def test_accounting_adjustments_export_returns_csv(self):
        self.login()

        run = ReconciliationRun.objects.create(
            tenant=self.tenant,
            status=ReconciliationRun.Status.COMPLETED,
        )
        ReconciliationIssueRecord.objects.create(
            run=run,
            severity=ReconciliationIssueRecord.Severity.HIGH,
            category=ReconciliationIssueRecord.Category.SETTLEMENT_GAP,
            title="Card settlement does not match POS sales",
            evidence=["POS card sales 1290.10; bank/card deposits 1280.10; short by 10.00."],
            recommended_action="Check processor batch timing.",
            related_transaction_ids=["pos-card", "bank-card"],
        )

        response = self.client.get(
            reverse("dashboard:run_accounting_adjustments_export", args=[run.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn(b"Suggested Account", response.content)
        self.assertIn(b"Card Clearing", response.content)

    def test_run_summary_print_page_renders(self):
        self.login()

        run = ReconciliationRun.objects.create(
            tenant=self.tenant,
            status=ReconciliationRun.Status.COMPLETED,
            summary={"import_count": 1, "transaction_count": 4, "issue_count": 1},
        )
        ReconciliationIssueRecord.objects.create(
            run=run,
            severity=ReconciliationIssueRecord.Severity.HIGH,
            category=ReconciliationIssueRecord.Category.SETTLEMENT_GAP,
            title="Card settlement does not match POS sales",
            evidence=["short by 10.00"],
            recommended_action="Check processor batch timing.",
            related_transaction_ids=["pos-card"],
        )

        response = self.client.get(reverse("dashboard:run_summary_print", args=[run.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Print / Save as PDF")
        self.assertContains(response, "Card settlement does not match POS sales")

    def test_run_detail_is_limited_to_user_tenant(self):
        other_tenant = Tenant.objects.create(name="Other Store")
        run = ReconciliationRun.objects.create(
            tenant=other_tenant,
            status=ReconciliationRun.Status.COMPLETED,
        )
        self.login()

        response = self.client.get(reverse("dashboard:run_detail", args=[run.pk]))

        self.assertEqual(response.status_code, 404)

    def test_run_history_lists_tenant_runs(self):
        self.login()
        run = ReconciliationRun.objects.create(
            tenant=self.tenant,
            status=ReconciliationRun.Status.COMPLETED,
            summary={"import_count": 1, "transaction_count": 4, "issue_count": 2},
        )
        other_tenant = Tenant.objects.create(name="Other Store")
        ReconciliationRun.objects.create(
            tenant=other_tenant,
            status=ReconciliationRun.Status.COMPLETED,
        )

        response = self.client.get(reverse("dashboard:run_history"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("dashboard:index"))
        self.assertContains(response, reverse("dashboard:invoice_generator"))
        self.assertContains(response, f"Run #{run.pk}")
        # The other tenant's run must not show up.
        self.assertEqual(
            response.content.count(b"Run #"),
            response.content.count(f"Run #{run.pk}".encode("utf-8")),
        )

    def test_run_detail_severity_filter_narrows_results(self):
        self.login()
        run = ReconciliationRun.objects.create(
            tenant=self.tenant,
            status=ReconciliationRun.Status.COMPLETED,
        )
        ReconciliationIssueRecord.objects.create(
            run=run,
            severity=ReconciliationIssueRecord.Severity.HIGH,
            category=ReconciliationIssueRecord.Category.SETTLEMENT_GAP,
            title="Card settlement does not match POS sales",
            evidence=["short by 10.00"],
            recommended_action="Check processor batch timing.",
            related_transaction_ids=["pos-card"],
        )
        ReconciliationIssueRecord.objects.create(
            run=run,
            severity=ReconciliationIssueRecord.Severity.MEDIUM,
            category=ReconciliationIssueRecord.Category.UNRESOLVED_SUSPENDED_SALE,
            title="Suspended sale remains unresolved after close",
            evidence=["2026-05-01 has suspended sales of 15.00."],
            recommended_action="Resolve the suspended transaction.",
            related_transaction_ids=["txn-1"],
        )

        response = self.client.get(
            reverse("dashboard:run_detail", args=[run.pk]) + "?severity=high"
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Card settlement does not match POS sales")
        self.assertNotContains(response, "Suspended sale remains unresolved after close")

    def test_update_issue_status_marks_resolved_and_writes_audit_event(self):
        self.login()
        run = ReconciliationRun.objects.create(
            tenant=self.tenant,
            status=ReconciliationRun.Status.COMPLETED,
        )
        issue = ReconciliationIssueRecord.objects.create(
            run=run,
            severity=ReconciliationIssueRecord.Severity.HIGH,
            category=ReconciliationIssueRecord.Category.SETTLEMENT_GAP,
            title="Card settlement does not match POS sales",
            evidence=["short by 10.00"],
            recommended_action="Check processor batch timing.",
            related_transaction_ids=["pos-card"],
        )

        with self.assertLogs("pos_reconciliation", level="INFO") as captured:
            response = self.client.post(
                reverse("dashboard:update_issue_status", args=[run.pk, issue.pk]),
                {"status": ReconciliationIssueRecord.Status.RESOLVED, "note": "Reissued deposit."},
            )

        self.assertRedirects(response, reverse("dashboard:run_detail", args=[run.pk]))
        issue.refresh_from_db()
        self.assertEqual(issue.status, ReconciliationIssueRecord.Status.RESOLVED)
        self.assertEqual(issue.resolution_note, "Reissued deposit.")
        self.assertTrue(
            AuditEvent.objects.filter(
                action=AuditEvent.Action.ISSUE_RESOLVED,
                run=run,
                issue=issue,
            ).exists()
        )
        self.assertTrue(any("issue_status_updated" in message for message in captured.output))

    def test_update_issue_status_rejects_unknown_value(self):
        self.login()
        run = ReconciliationRun.objects.create(
            tenant=self.tenant,
            status=ReconciliationRun.Status.COMPLETED,
        )
        issue = ReconciliationIssueRecord.objects.create(
            run=run,
            severity=ReconciliationIssueRecord.Severity.HIGH,
            category=ReconciliationIssueRecord.Category.SETTLEMENT_GAP,
            title="Card settlement does not match POS sales",
            evidence=["short by 10.00"],
            recommended_action="Check processor batch timing.",
            related_transaction_ids=["pos-card"],
        )

        response = self.client.post(
            reverse("dashboard:update_issue_status", args=[run.pk, issue.pk]),
            {"status": "bogus"},
        )

        self.assertEqual(response.status_code, 400)
        issue.refresh_from_db()
        self.assertEqual(issue.status, ReconciliationIssueRecord.Status.OPEN)
