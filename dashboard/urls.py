from django.urls import path

from dashboard import views


app_name = "dashboard"

urlpatterns = [
    path("", views.index, name="index"),
    path("runs/<int:pk>/", views.run_detail, name="run_detail"),
    path("runs/<int:pk>/issues.csv", views.run_issues_export, name="run_issues_export"),
]
