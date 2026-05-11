from django.db import models


class Tenant(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "id"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = _slugify_name(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Membership(models.Model):
    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        STAFF = "staff", "Staff"
        ACCOUNTANT = "accountant", "Accountant"

    tenant = models.ForeignKey(Tenant, related_name="memberships", on_delete=models.CASCADE)
    user = models.ForeignKey(
        "auth.User",
        related_name="memberships",
        on_delete=models.CASCADE,
    )
    role = models.CharField(max_length=24, choices=Role.choices, default=Role.STAFF)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["tenant", "user"], name="unique_tenant_user_membership")
        ]

    def __str__(self):
        return f"{self.user} in {self.tenant} ({self.role})"


class ImportFile(models.Model):
    class SourceType(models.TextChoices):
        POS_DAILY = "pos_daily", "POS daily"
        CARD_BANK = "card_bank", "Card/bank"
        WOOCOMMERCE = "woocommerce", "WooCommerce"
        FUEL_INVOICE = "fuel_invoice", "Fuel invoice"
        LOTTERY_SETTLEMENT = "lottery_settlement", "Lottery settlement"
        EXPENSE = "expense", "Expense"

    class Status(models.TextChoices):
        RECEIVED = "received", "Received"
        PROCESSED = "processed", "Processed"
        FAILED = "failed", "Failed"

    tenant = models.ForeignKey(
        Tenant,
        related_name="import_files",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )
    source_type = models.CharField(max_length=32, choices=SourceType.choices)
    original_filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=120)
    file_size = models.PositiveIntegerField()
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.RECEIVED)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.get_source_type_display()} import: {self.original_filename}"


class CanonicalTransactionRecord(models.Model):
    class Category(models.TextChoices):
        SALE = "sale", "Sale"
        DEPOSIT = "deposit", "Deposit"
        INVOICE = "invoice", "Invoice"
        SETTLEMENT = "settlement", "Settlement"
        EXPENSE = "expense", "Expense"
        ADJUSTMENT = "adjustment", "Adjustment"

    class TenderType(models.TextChoices):
        CASH = "cash", "Cash"
        CARD = "card", "Card"
        BANK = "bank", "Bank"
        FUEL = "fuel", "Fuel"
        LOTTERY = "lottery", "Lottery"
        ONLINE = "online", "Online"
        MIXED = "mixed", "Mixed"
        UNKNOWN = "unknown", "Unknown"

    import_file = models.ForeignKey(
        ImportFile,
        related_name="transactions",
        on_delete=models.CASCADE,
    )
    source_transaction_id = models.CharField(max_length=255)
    source_type = models.CharField(max_length=32, choices=ImportFile.SourceType.choices)
    business_date = models.DateField()
    posted_at = models.DateTimeField()
    category = models.CharField(max_length=24, choices=Category.choices)
    tender_type = models.CharField(max_length=24, choices=TenderType.choices)
    external_ref = models.CharField(max_length=255, null=True, blank=True)
    payee_key = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["business_date", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["import_file", "source_transaction_id"],
                name="unique_transaction_per_import",
            )
        ]
        indexes = [
            models.Index(fields=["business_date", "category", "tender_type"]),
            models.Index(fields=["external_ref"]),
            models.Index(fields=["payee_key"]),
        ]

    def __str__(self):
        return f"{self.business_date} {self.category} {self.amount}"


class ReconciliationRun(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    tenant = models.ForeignKey(
        Tenant,
        related_name="reconciliation_runs",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )
    import_files = models.ManyToManyField(ImportFile, related_name="reconciliation_runs", blank=True)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.PENDING)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    summary = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"Reconciliation run #{self.pk} ({self.status})"


class ReconciliationIssueRecord(models.Model):
    class Severity(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    class Category(models.TextChoices):
        MISSING_ENTRY = "missing_entry", "Missing entry"
        DUPLICATE_ENTRY = "duplicate_entry", "Duplicate entry"
        TOTAL_MISMATCH = "total_mismatch", "Total mismatch"
        SETTLEMENT_GAP = "settlement_gap", "Settlement gap"
        SUSPICIOUS_TOTAL = "suspicious_total", "Suspicious total"
        UNRESOLVED_SUSPENDED_SALE = "unresolved_suspended_sale", "Unresolved suspended sale"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        RESOLVED = "resolved", "Resolved"
        DISMISSED = "dismissed", "Dismissed"

    run = models.ForeignKey(
        ReconciliationRun,
        related_name="issues",
        on_delete=models.CASCADE,
    )
    severity = models.CharField(max_length=16, choices=Severity.choices)
    category = models.CharField(max_length=48, choices=Category.choices)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.OPEN)
    title = models.CharField(max_length=255)
    evidence = models.JSONField(default=list)
    recommended_action = models.TextField()
    related_transaction_ids = models.JSONField(default=list, blank=True)
    resolution_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["severity", "category", "id"]
        indexes = [
            models.Index(fields=["run", "severity", "status"]),
            models.Index(fields=["category"]),
        ]

    def __str__(self):
        return f"{self.severity}: {self.title}"


class AuditEvent(models.Model):
    class Action(models.TextChoices):
        IMPORT_CREATED = "import_created", "Import created"
        IMPORT_PROCESSED = "import_processed", "Import processed"
        RUN_CREATED = "run_created", "Run created"
        ISSUE_RESOLVED = "issue_resolved", "Issue resolved"
        ISSUE_DISMISSED = "issue_dismissed", "Issue dismissed"
        EXPORT_CREATED = "export_created", "Export created"

    tenant = models.ForeignKey(
        Tenant,
        related_name="audit_events",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )
    action = models.CharField(max_length=48, choices=Action.choices)
    actor_label = models.CharField(max_length=120, default="system")
    import_file = models.ForeignKey(
        ImportFile,
        related_name="audit_events",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    run = models.ForeignKey(
        ReconciliationRun,
        related_name="audit_events",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    issue = models.ForeignKey(
        ReconciliationIssueRecord,
        related_name="audit_events",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["action", "created_at"]),
        ]

    def __str__(self):
        return f"{self.action} by {self.actor_label}"


def _slugify_name(value):
    slug = "".join(character.lower() if character.isalnum() else "-" for character in value)
    return "-".join(part for part in slug.split("-") if part)
