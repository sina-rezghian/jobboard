from .models import Notification


def notifications_nav(request):
    if not request.user.is_authenticated:
        return {"nav_recent_notifications": [], "nav_unread_notifications": 0, "ui_dir": request.session.get("ui_dir", "rtl")}

    qs = Notification.objects.filter(user=request.user).order_by("-created_at")
    return {
        "nav_recent_notifications": qs[:5],
        "nav_unread_notifications": qs.filter(is_read=False).count(),
        "ui_dir": request.session.get("ui_dir", "rtl"),
    }
