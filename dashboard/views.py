from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from dashboard.services import IMPORTERS, get_user_tenant, process_uploaded_import
from imports.models import ImportFile, ReconciliationRun
from reconciliation.exports import issues_to_csv
from reconciliation.types import ReconciliationIssue


@login_required
def index(request):
    if request.method == "POST":
        source_type = request.POST.get("source_type", "")
        source_file = request.FILES.get("source_file")
        if not source_file:
            messages.error(request, "Choose a CSV file before starting a reconciliation run.")
        elif source_type not in IMPORTERS:
            messages.error(request, "Choose a supported source type.")
        else:
            run = process_uploaded_import(source_type, source_file, user=request.user)
            return redirect("dashboard:run_detail", pk=run.pk)

    return render(
        request,
        "dashboard/index.html",
        {
            "page_title": "AI POS Reconciliation Assistant",
            "source_types": [
                choice
                for choice in ImportFile.SourceType.choices
                if choice[0] in IMPORTERS
            ],
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
    return render(
        request,
        "dashboard/run_detail.html",
        {
            "page_title": f"Run #{run.pk}",
            "run": run,
            "issues": run.issues.all(),
        },
    )


@login_required
def run_issues_export(request, pk):
    tenant = get_user_tenant(request.user)
    run = get_object_or_404(
        ReconciliationRun.objects.prefetch_related("issues"),
        tenant=tenant,
        pk=pk,
    )
    content = issues_to_csv(
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
    )
    response = HttpResponse(content, content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="reconciliation-run-{run.pk}-issues.csv"'
    return response
