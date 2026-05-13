from django.urls import path

from dashboard import views


app_name = "dashboard"

urlpatterns = [
    path("", views.index, name="index"),
    path("runs/", views.run_history, name="run_history"),
    path("runs/<int:pk>/", views.run_detail, name="run_detail"),
    path("runs/<int:pk>/issues.csv", views.run_issues_export, name="run_issues_export"),
    path(
        "runs/<int:pk>/accounting-adjustments.csv",
        views.run_accounting_adjustments_export,
        name="run_accounting_adjustments_export",
    ),
    path("runs/<int:pk>/summary", views.run_summary_print, name="run_summary_print"),
    path(
        "runs/<int:run_pk>/issues/<int:issue_pk>/status",
        views.update_issue_status,
        name="update_issue_status",
    ),
]
