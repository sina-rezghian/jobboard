import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.tokens import default_token_generator
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.views.decorators.http import require_http_methods, require_POST

from jobboard.email_demo import send_email_demo
from jobboard.sms_demo import send_sms_demo

from .forms import EmployerRegistrationForm, JobSeekerRegistrationForm, LoginForm
from .models import EmployerProfile, JobSeekerProfile, Notification

logger = logging.getLogger(__name__)
User = get_user_model()


def _send_activation_email(request, user: User) -> None:
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    link = request.build_absolute_uri(
        reverse("activate_account", kwargs={"uidb64": uidb64, "token": token})
    )

    subject = "Activate your JobBoard account"
    message = (
        f"Hi {user.username},\n\n"
        f"Please activate your account using this link:\n{link}\n\n"
        "If you did not sign up, you can ignore this email."
    )
    # Console backend prints the email; we ALSO persist it to logs as a demo artifact.
    send_email_demo(
        to_email=user.email,
        subject=subject,
        message=message,
        tag="EMAIL_ACTIVATION",
        meta={
            "user_id": user.pk,
            "username": user.username,
            "role": getattr(user, "role", None),
            "activation_link": link,
        },
        from_email=settings.DEFAULT_FROM_EMAIL,
    )


def signup_choose(request):
    """Single entry-point for signup: user chooses Employer vs Job Seeker."""
    return render(request, "accounts/signup_choose.html")


# -----------------------------
# Register Employer (Phase 4: email verification)
# -----------------------------
@require_http_methods(["GET", "POST"])
def register_employer(request):
    if request.method == "POST":
        form = EmployerRegistrationForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"]
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]

            # create user (inactive until activation)
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                is_active=False,
                role=User.Role.EMPLOYER,
            )

            employer_profile = form.save(commit=False)
            employer_profile.user = user
            employer_profile.save()

            _send_activation_email(request, user)
            logger.info("Employer registered (pending activation): username=%s email=%s", username, email)

            messages.success(
                request,
                "Registered! Please check your email to activate your account. "
                "If needed, request an SMS code from the login page (demo).",
            )
            return redirect("login")
        logger.warning("Employer registration failed: errors=%s", form.errors)
    else:
        form = EmployerRegistrationForm()

    return render(request, "accounts/register_employer.html", {"form": form})


# -----------------------------
# Register JobSeeker (Phase 4: email verification)
# -----------------------------
@require_http_methods(["GET", "POST"])
def register_jobseeker(request):
    if request.method == "POST":
        form = JobSeekerRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            username = form.cleaned_data["username"]
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]

            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                is_active=False,
                role=User.Role.JOBSEEKER,
            )

            jobseeker_profile = form.save(commit=False)
            jobseeker_profile.user = user
            jobseeker_profile.save()

            _send_activation_email(request, user)
            logger.info("JobSeeker registered (pending activation): username=%s email=%s", username, email)

            messages.success(
                request,
                "Registered! Please check your email to activate your account. "
                "If needed, request an SMS code from the login page (demo).",
            )
            return redirect("login")
        logger.warning("JobSeeker registration failed: errors=%s", form.errors)
    else:
        form = JobSeekerRegistrationForm()

    return render(request, "accounts/register_jobseeker.html", {"form": form})


# -----------------------------
# Activate Account (Phase 4)
# -----------------------------
@require_http_methods(["GET"])
def activate_account(request, uidb64: str, token: str):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except Exception:
        user = None

    if user is None:
        logger.warning("Activation failed: invalid uid")
        messages.error(request, "Activation link is invalid.")
        return redirect("login")

    if default_token_generator.check_token(user, token):
        user.is_active = True
        user.is_email_verified = True
        user.save(update_fields=["is_active", "is_email_verified"])
        logger.info("Account activated: username=%s email=%s", user.username, user.email)
        messages.success(request, "Your account has been activated. You can now log in.")
        return redirect("login")

    logger.warning("Activation failed: bad token for username=%s", user.username)
    messages.error(request, "Activation link is invalid or expired.")
    return redirect("login")


# -----------------------------
# Login View (Phase 3: session management)
# -----------------------------
@require_http_methods(["GET", "POST"])
def user_login(request):
    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"]
            password = form.cleaned_data["password"]

            user = authenticate(request, username=username, password=password)
            if user:
                if not user.is_active:
                    messages.error(request, "Your account is not active. Please activate it from your email.")
                    logger.info("Login blocked (inactive): username=%s", username)
                    return redirect("login")

                login(request, user)

                # Session management: explicit expiry (1 hour by default)
                request.session.set_expiry(getattr(settings, "SESSION_COOKIE_AGE", 3600))
                request.session["role"] = getattr(user, "role", "")
                logger.info("Login success: username=%s role=%s", user.username, getattr(user, "role", ""))

                messages.success(request, "Logged in successfully!")
                return redirect("home")
            messages.error(request, "Invalid username or password.")
            logger.info("Login failed: username=%s", username)
    else:
        form = LoginForm()

    return render(request, "accounts/login.html", {"form": form})


# -----------------------------
# Logout View
# -----------------------------
@require_http_methods(["POST", "GET"])
def user_logout(request):
    username = request.user.username if request.user.is_authenticated else None
    logout(request)
    if username:
        logger.info("Logout: username=%s", username)
    messages.info(request, "Logged out successfully.")
    return redirect("login")



def sms_activate(request):
    """Activate user by demo SMS code (extra/bonus feature).

    The code is sent on-demand by calling sms_send_code.
    """
    if request.method == "POST":
        username = (request.POST.get("username") or "").strip()
        code = (request.POST.get("code") or "").strip()

        if not username or not code:
            messages.error(request, "Please enter username and code.")
            return redirect("sms_activate")

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            messages.error(request, "User not found.")
            return redirect("sms_activate")

        ttl_seconds = max(60, int(getattr(settings, "SMS_ACTIVATION_TTL_SECONDS", 600)))
        cached = cache.get(f"sms_activation:{user.pk}")
        persisted = (user.sms_activation_code or "").strip()
        sent_at = user.sms_activation_sent_at
        persisted_valid = bool(
            persisted
            and sent_at
            and (timezone.now() - sent_at) <= timedelta(seconds=ttl_seconds)
        )

        if not cached and not persisted_valid:
            messages.error(request, "No active code found (expired). Please register again or use email activation.")
            return redirect("sms_activate")

        valid_codes = set()
        if cached:
            valid_codes.add(str(cached))
        if persisted_valid:
            valid_codes.add(str(persisted))
        if code not in valid_codes:
            messages.error(request, "Invalid code.")
            return redirect("sms_activate")

        user.is_active = True
        user.is_email_verified = True
        user.sms_activation_code = None
        user.sms_activation_sent_at = None
        user.save(update_fields=["is_active", "is_email_verified", "sms_activation_code", "sms_activation_sent_at"])

        cache.delete(f"sms_activation:{user.pk}")
        login(request, user)
        request.session.set_expiry(getattr(settings, "SESSION_COOKIE_AGE", 3600))
        request.session["role"] = getattr(user, "role", "")
        messages.success(request, "Account activated successfully and you are now logged in.")
        return redirect("home")

    return render(request, "accounts/sms_activate.html")


def home(request):
    return render(request, "accounts/home.html")


def _get_activation_phone(user: User) -> str | None:
    role = getattr(user, "role", "")
    if role == User.Role.EMPLOYER:
        profile = EmployerProfile.objects.filter(user=user).only("phone").first()
        return (profile.phone or "").strip() if profile and profile.phone else None
    if role == User.Role.JOBSEEKER:
        profile = JobSeekerProfile.objects.filter(user=user).only("phone").first()
        return (profile.phone or "").strip() if profile and profile.phone else None
    return None


def _generate_unique_sms_code(user: User) -> str:
    existing = {
        str(cache.get(f"sms_activation:{user.pk}") or "").strip(),
        str(user.sms_activation_code or "").strip(),
    }
    for _ in range(20):
        code = f"{secrets.randbelow(900000) + 100000:06d}"
        if code not in existing:
            return code
    return f"{secrets.randbelow(900000) + 100000:06d}"


def _send_demo_sms_activation(user: User, phone: str | None) -> str:
    """Demo SMS activation: generates a code and logs it (no paid provider needed).

    The code is stored in Django cache and persisted to DB with TTL enforcement.
    """
    ttl_seconds = max(60, int(getattr(settings, "SMS_ACTIVATION_TTL_SECONDS", 600)))
    code = _generate_unique_sms_code(user)
    cache.set(f"sms_activation:{user.pk}", code, timeout=ttl_seconds)
    user.sms_activation_code = code
    user.sms_activation_sent_at = timezone.now()
    user.save(update_fields=["sms_activation_code", "sms_activation_sent_at"])

    # In a real project: integrate an SMS provider (Kavenegar/Twilio/etc.)
    send_sms_demo(
        (phone or "(no-phone)"),
        f"Activation code for {user.username}: {code}",
        tag="ACTIVATION",
        meta={"user_id": user.pk, "username": user.username, "role": getattr(user, "role", None)},
    )
    logger.info(
        "SMS activation code generated: username=%s code=%s ttl=%ss",
        user.username,
        code,
        ttl_seconds,
    )
    return code


@require_POST
def sms_send_code(request):
    """Issue a new SMS activation code on explicit user request."""
    username = (request.POST.get("username") or "").strip()
    if not username:
        return JsonResponse({"ok": False, "message": "Please enter your username first."}, status=400)

    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return JsonResponse({"ok": False, "message": "User not found."}, status=404)

    if user.is_active and user.is_email_verified:
        return JsonResponse(
            {"ok": False, "message": "Your account is already active. Please login."},
            status=400,
        )

    phone = _get_activation_phone(user)
    _send_demo_sms_activation(user, phone)
    return JsonResponse(
        {
            "ok": True,
            "message": "Code sent. Check terminal output and logs/sms_demo.log.",
        }
    )




# -----------------------------
# UI helpers (Indeed-like)
# -----------------------------
@login_required
def notifications_list(request):
    qs = Notification.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "accounts/notifications.html", {"notifications": qs})

@login_required
@require_POST
def notification_mark_read(request, notification_id):
    notif = get_object_or_404(Notification, id=notification_id, user=request.user)
    notif.is_read = True
    notif.save(update_fields=["is_read"])
    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or "/"
    return redirect(next_url)

@login_required
@require_POST
def notifications_mark_all_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or "/"
    return redirect(next_url)

def toggle_ui_dir(request):
    # simple RTL/LTR toggle stored in session
    cur = request.session.get("ui_dir")
    request.session["ui_dir"] = "rtl" if cur != "rtl" else "ltr"
    next_url = request.GET.get("next") or request.META.get("HTTP_REFERER") or "/"
    return redirect(next_url)
