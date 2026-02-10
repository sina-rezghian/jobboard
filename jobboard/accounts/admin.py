from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User, EmployerProfile, JobSeekerProfile, Notification


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    # show extra fields in admin
    fieldsets = DjangoUserAdmin.fieldsets + (
        ("JobBoard", {"fields": ("role", "is_email_verified")}),
    )
    list_display = ("username", "email", "role", "is_active", "is_email_verified", "is_staff")


admin.site.register(EmployerProfile)
admin.site.register(JobSeekerProfile)

admin.site.register(Notification)
