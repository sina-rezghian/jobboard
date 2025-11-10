from django.urls import path
from . import views

urlpatterns = [
    path('register/employer/', views.register_employer, name='register_employer'),
    path('register/jobseeker/', views.register_jobseeker, name='register_jobseeker'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
]
