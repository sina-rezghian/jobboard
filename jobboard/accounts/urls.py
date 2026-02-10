from django.urls import path
from . import views

urlpatterns = [
    path("notifications/", views.notifications_list, name="notifications_list"),
    path("notifications/mark-all-read/", views.notifications_mark_all_read, name="notifications_mark_all_read"),
    path("notifications/<int:notification_id>/read/", views.notification_mark_read, name="notification_mark_read"),
    path("toggle-dir/", views.toggle_ui_dir, name="toggle_ui_dir"),
    path("register/employer/", views.register_employer, name="register_employer"),
    path("register/jobseeker/", views.register_jobseeker, name="register_jobseeker"),
    path("signup/", views.signup_choose, name="signup_choose"),
    path("activate/<uidb64>/<token>/", views.activate_account, name="activate_account"),
    path("sms-activate/", views.sms_activate, name="sms_activate"),
    path("sms-activate/send-code/", views.sms_send_code, name="sms_send_code"),
    path("login/", views.user_login, name="login"),
    path("logout/", views.user_logout, name="logout"),
]
