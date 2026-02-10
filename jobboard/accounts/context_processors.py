from django.db.models import Count
from .models import Notification

def notifications_nav(request):
    if not getattr(request, "user", None) or not request.user.is_authenticated:
        return {"nav_unread_notifications": 0, "nav_recent_notifications": [], "ui_dir": request.session.get('ui_dir','')}
    qs = Notification.objects.filter(user=request.user)
    unread = qs.filter(is_read=False).count()
    recent = list(qs[:5])
    return {"nav_unread_notifications": unread, "nav_recent_notifications": recent, "ui_dir": request.session.get('ui_dir','')}
