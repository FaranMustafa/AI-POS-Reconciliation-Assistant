from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from imports.models import (
    AuditEvent,
    CanonicalTransactionRecord,
    ImportFile,
    Membership,
    ReconciliationIssueRecord,
    ReconciliationRun,
    Tenant,
)


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

    def test_index_displays_upload_form(self):
        self.login()

        response = self.client.get(reverse("dashboard:index"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "New reconciliation run")
        self.assertContains(response, 'name="source_type"')
        self.assertContains(response, 'name="source_file"')
        self.assertNotContains(response, "Expense")

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

    def test_run_detail_is_limited_to_user_tenant(self):
        other_tenant = Tenant.objects.create(name="Other Store")
        run = ReconciliationRun.objects.create(
            tenant=other_tenant,
            status=ReconciliationRun.Status.COMPLETED,
        )
        self.login()

        response = self.client.get(reverse("dashboard:run_detail", args=[run.pk]))

        self.assertEqual(response.status_code, 404)
