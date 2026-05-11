from django.contrib import admin

from imports.models import (
    AuditEvent,
    CanonicalTransactionRecord,
    ImportFile,
    ReconciliationIssueRecord,
    ReconciliationRun,
)


@admin.register(ImportFile)
class ImportFileAdmin(admin.ModelAdmin):
    list_display = ("original_filename", "source_type", "status", "file_size", "created_at")
    list_filter = ("source_type", "status", "created_at")
    search_fields = ("original_filename", "error_message")


@admin.register(CanonicalTransactionRecord)
class CanonicalTransactionRecordAdmin(admin.ModelAdmin):
    list_display = ("business_date", "category", "tender_type", "amount", "source_type")
    list_filter = ("source_type", "category", "tender_type", "business_date")
    search_fields = ("source_transaction_id", "external_ref", "payee_key", "description")


@admin.register(ReconciliationRun)
class ReconciliationRunAdmin(admin.ModelAdmin):
    list_display = ("id", "status", "created_at", "completed_at")
    list_filter = ("status", "created_at")
    filter_horizontal = ("import_files",)


@admin.register(ReconciliationIssueRecord)
class ReconciliationIssueRecordAdmin(admin.ModelAdmin):
    list_display = ("title", "severity", "category", "status", "created_at")
    list_filter = ("severity", "category", "status", "created_at")
    search_fields = ("title", "recommended_action")


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ("action", "actor_label", "created_at")
    list_filter = ("action", "created_at")
    search_fields = ("actor_label",)

