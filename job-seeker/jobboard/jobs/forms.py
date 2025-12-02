from django import forms
from .models import Job, JobApplication

class JobCreateForm(forms.ModelForm):
    class Meta:
        model = Job
        fields = ['title', 'description', 'location']


class JobApplicationForm(forms.ModelForm):
    class Meta:
        model = JobApplication
        fields = ['resume', 'cover_letter']
