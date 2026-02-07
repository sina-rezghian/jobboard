from django.urls import path
from . import views

urlpatterns = [
    path("create/", views.create_job, name="create_job"),
    path("my-jobs/", views.employer_jobs, name="employer_jobs"),
    path("edit/<int:job_id>/", views.edit_job, name="edit_job"),

    path("list/", views.job_list, name="job_list"),
    path("recommended/", views.recommended_jobs, name="recommended_jobs"),
    path("<int:job_id>/", views.job_detail, name="job_detail"),
    path("apply/<int:job_id>/", views.apply_job, name="apply_job"),

    path("my-applications/", views.my_applications, name="my_applications"),
    path("all-applications/", views.employer_applications, name="employer_applications"),
    path("sms-log/", views.employer_sms_log, name="employer_sms_log"),

    path("saved/", views.saved_jobs, name="saved_jobs"),
    path("save/<int:job_id>/", views.toggle_saved_job, name="toggle_saved_job"),
    path("alerts/", views.job_alerts, name="job_alerts"),
    path("alerts/delete/<int:alert_id>/", views.delete_job_alert, name="delete_job_alert"),
    path("alerts/inbox/", views.alert_inbox, name="alert_inbox"),
    path("dashboard/", views.dashboard, name="dashboard"),

    path("application/<int:application_id>/", views.application_detail, name="application_detail"),
    path("applications/<int:job_id>/", views.view_applications, name="view_applications"),
    path("application/<int:application_id>/schedule/", views.schedule_interview, name="schedule_interview"),
    path("application/<int:application_id>/reject/", views.reject_application, name="reject_application"),
]
