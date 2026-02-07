from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from accounts import views as accounts_views
from jobs import views as job_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', job_views.home_public, name='home'),   # landing page
    path('accounts/', include('accounts.urls')),
    path('jobs/', include('jobs.urls')),
    path('resumes/', include('resumes.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
