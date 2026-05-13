from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from dashboard.services import (
    IMPORTERS,
    PastedTabularUpload,
    get_user_tenant,
    process_uploaded_run,
)
from imports.models import (
    AuditEvent,
    ImportFile,
    ReconciliationIssueRecord,
    ReconciliationRun,
)
from reconciliation.exports import (
    issues_to_accounting_adjustment_csv,
    issues_to_csv,
)
from reconciliation.types import ReconciliationIssue


@login_required
def index(request):
    if request.method == "POST":
        uploads = _collect_uploads(request)
        if uploads is None:
            return render(
                request,
                "dashboard/index.html",
                _index_context(),
            )
        run = process_uploaded_run(
            uploads,
            user=request.user,
            run_immediately=request.POST.get("processing_mode") != "queued",
        )
        return redirect("dashboard:run_detail", pk=run.pk)

    return render(request, "dashboard/index.html", _index_context())


def _index_context():
    return {
        "page_title": "AI POS Reconciliation Assistant",
        "source_types": [
            choice
            for choice in ImportFile.SourceType.choices
            if choice[0] in IMPORTERS
        ],
    }


def _collect_uploads(request):
    """Read the upload form into ``[(source_type, file), ...]`` or set messages on errors."""

    single_source_type = request.POST.get("source_type", "")
    single_file = request.FILES.get("source_file")
    multi_source_types = request.POST.getlist("multi_source_type")
    multi_files = request.FILES.getlist("multi_source_file")

    uploads = []
    if single_file:
        if single_source_type not in IMPORTERS:
            messages.error(request, "Choose a supported source type.")
            return None
        uploads.append((single_source_type, single_file))

    for source_type, uploaded_file in zip(multi_source_types, multi_files):
        if not uploaded_file:
            continue
        if source_type not in IMPORTERS:
            messages.error(request, f"Unsupported source type: {source_type}.")
            return None
        uploads.append((source_type, uploaded_file))

    if not uploads:
        pasted_source_type = request.POST.get("pasted_source_type", "")
        pasted_content = request.POST.get("pasted_content", "").strip()
        if pasted_content:
            if pasted_source_type not in IMPORTERS:
                messages.error(request, "Choose a supported source type for pasted text.")
                return None
            uploads.append(
                (
                    pasted_source_type,
                    PastedTabularUpload(
                        name=f"pasted-{pasted_source_type}.txt",
                        content=pasted_content,
                    ),
                )
            )

    if not uploads:
        messages.error(
            request,
            "Choose at least one CSV file before starting a reconciliation run.",
        )
        return None
    return uploads


@login_required
def run_history(request):
    tenant = get_user_tenant(request.user)
    runs = (
        ReconciliationRun.objects.filter(tenant=tenant)
        .order_by("-created_at", "-id")
        .prefetch_related("import_files", "issues")
    )
    return render(
        request,
        "dashboard/run_history.html",
        {
            "page_title": "Reconciliation runs",
            "runs": runs,
        },
    )


@login_required
def run_detail(request, pk):
    tenant = get_user_tenant(request.user)
    run = get_object_or_404(
        ReconciliationRun.objects.prefetch_related("import_files", "issues"),
        tenant=tenant,
        pk=pk,
    )

    severity_filter = request.GET.get("severity", "")
    category_filter = request.GET.get("category", "")
    status_filter = request.GET.get("status", "")

    issue_qs = run.issues.all()
    if severity_filter in dict(ReconciliationIssueRecord.Severity.choices):
        issue_qs = issue_qs.filter(severity=severity_filter)
    if category_filter in dict(ReconciliationIssueRecord.Category.choices):
        issue_qs = issue_qs.filter(category=category_filter)
    if status_filter in dict(ReconciliationIssueRecord.Status.choices):
        issue_qs = issue_qs.filter(status=status_filter)

    all_issues = list(run.issues.all())
    severity_counts = _counts_by(all_issues, "severity")
    category_counts = _counts_by(all_issues, "category")
    status_counts = _counts_by(all_issues, "status")

    return render(
        request,
        "dashboard/run_detail.html",
        {
            "page_title": f"Run #{run.pk}",
            "run": run,
            "issues": issue_qs,
            "severity_choices": ReconciliationIssueRecord.Severity.choices,
            "category_choices": ReconciliationIssueRecord.Category.choices,
            "status_choices": ReconciliationIssueRecord.Status.choices,
            "severity_filter": severity_filter,
            "category_filter": category_filter,
            "status_filter": status_filter,
            "severity_counts": severity_counts,
            "category_counts": category_counts,
            "status_counts": status_counts,
            "total_issues": len(all_issues),
        },
    )


def _counts_by(issues, attribute):
    counts = {}
    for issue in issues:
        key = getattr(issue, attribute)
        counts[key] = counts.get(key, 0) + 1
    return counts


@login_required
@require_POST
def update_issue_status(request, run_pk, issue_pk):
    tenant = get_user_tenant(request.user)
    run = get_object_or_404(ReconciliationRun, tenant=tenant, pk=run_pk)
    issue = get_object_or_404(ReconciliationIssueRecord, run=run, pk=issue_pk)

    new_status = request.POST.get("status", "")
    if new_status not in dict(ReconciliationIssueRecord.Status.choices):
        return HttpResponseBadRequest("Invalid status.")

    note = request.POST.get("note", "")
    issue.status = new_status
    if note:
        issue.resolution_note = note
    issue.save(update_fields=["status", "resolution_note", "updated_at"])

    if new_status == ReconciliationIssueRecord.Status.RESOLVED:
        action = AuditEvent.Action.ISSUE_RESOLVED
    elif new_status == ReconciliationIssueRecord.Status.DISMISSED:
        action = AuditEvent.Action.ISSUE_DISMISSED
    else:
        action = None

    if action is not None:
        AuditEvent.objects.create(
            tenant=tenant,
            action=action,
            run=run,
            issue=issue,
            actor_label=getattr(request.user, "username", "") or "system",
            metadata={"status": new_status, "note": note, "at": timezone.now().isoformat()},
        )

    messages.success(request, f"Issue marked as {issue.get_status_display().lower()}.")
    redirect_target = request.POST.get("next") or "dashboard:run_detail"
    if redirect_target.startswith("/"):
        return redirect(redirect_target)
    return redirect("dashboard:run_detail", pk=run.pk)


@login_required
def run_issues_export(request, pk):
    run, issues = _run_with_domain_issues(request.user, pk)
    content = issues_to_csv(issues)
    response = HttpResponse(content, content_type="text/csv")
    response["Content-Disposition"] = (
        f'attachment; filename="reconciliation-run-{run.pk}-issues.csv"'
    )
    return response


@login_required
def run_accounting_adjustments_export(request, pk):
    run, issues = _run_with_domain_issues(request.user, pk)
    content = issues_to_accounting_adjustment_csv(issues)
    response = HttpResponse(content, content_type="text/csv")
    response["Content-Disposition"] = (
        f'attachment; filename="reconciliation-run-{run.pk}-accounting-adjustments.csv"'
    )
    return response


@login_required
def run_summary_print(request, pk):
    tenant = get_user_tenant(request.user)
    run = get_object_or_404(
        ReconciliationRun.objects.prefetch_related("import_files", "issues"),
        tenant=tenant,
        pk=pk,
    )
    return render(
        request,
        "dashboard/run_summary_print.html",
        {
            "page_title": f"Run #{run.pk} summary",
            "run": run,
            "issues": run.issues.all(),
        },
    )


def _run_with_domain_issues(user, pk):
    tenant = get_user_tenant(user)
    run = get_object_or_404(
        ReconciliationRun.objects.prefetch_related("issues"),
        tenant=tenant,
        pk=pk,
    )
    issues = [
        ReconciliationIssue(
            id=f"issue-record-{issue.id}",
            run_id=str(run.id),
            severity=issue.severity,
            category=issue.category,
            title=issue.title,
            evidence=issue.evidence,
            recommended_action=issue.recommended_action,
            related_transaction_ids=issue.related_transaction_ids,
        )
        for issue in run.issues.all()
    ]
    return run, issues
