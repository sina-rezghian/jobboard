from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


def _role_required(role):
    def deco(view_func):
        @login_required
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            if getattr(request.user, "role", "") != role:
                messages.error(request, "Access denied.")
                return redirect("home")
            return view_func(request, *args, **kwargs)

        return wrapped

    return deco


employer_required = _role_required("employer")
jobseeker_required = _role_required("jobseeker")
