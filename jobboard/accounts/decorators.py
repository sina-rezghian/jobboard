from functools import wraps
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from .models import User, EmployerProfile, JobSeekerProfile

def role_required(role: str):
    """Ensure logged-in user has the given role."""
    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            user = request.user
            if not hasattr(user, "role") or user.role != role:
                messages.error(request, "Access denied.")
                return redirect("home")
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator

employer_required = role_required(User.Role.EMPLOYER)
jobseeker_required = role_required(User.Role.JOBSEEKER)

def get_employer_profile(user):
    return EmployerProfile.objects.get(user=user)

def get_jobseeker_profile(user):
    return JobSeekerProfile.objects.get(user=user)
