# jobs/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('create/', views.create_job, name='create_job'),
    path('my-jobs/', views.employer_jobs, name='employer_jobs'),
    path('list/', views.job_list, name='job_list'),
    path('<int:job_id>/', views.job_detail, name='job_detail'),
    path('apply/<int:job_id>/', views.apply_job, name='apply_job'),
    path('applications/<int:job_id>/', views.view_applications, name='view_applications'),
    path('application/<int:application_id>/schedule/', views.schedule_interview, name='schedule_interview'),
    path('application/<int:application_id>/reject/', views.reject_application, name='reject_application'),
]
