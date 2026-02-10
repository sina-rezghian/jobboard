from django.contrib import admin
from .models import Job, JobApplication, ApplicationNote

admin.site.register(Job)
admin.site.register(JobApplication)


from .models import SavedJob, JobAlert, JobAlertMatch, JobApplicationEvent

admin.site.register(SavedJob)
admin.site.register(JobAlert)
admin.site.register(JobAlertMatch)
admin.site.register(JobApplicationEvent)

admin.site.register(ApplicationNote)
