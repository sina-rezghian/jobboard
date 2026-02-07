from django import forms

from .constants import ENGLAND_CITIES, UK_CITIES
from .models import Job, JobApplication


class _BootstrapMixin:
    def _bootstrap(self):
        for name, field in self.fields.items():
            widget = field.widget
            css = widget.attrs.get("class", "")
            # avoid adding form-control to checkbox/radio
            if widget.__class__.__name__ in {"CheckboxInput", "RadioSelect"}:
                continue
            widget.attrs["class"] = (css + " form-control").strip()


class JobForm(_BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Job
        fields = [
            "title",
            "description",
            "location",
            "job_type",
            "experience_level",
            "cover_letter_required",
            "min_salary",
            "max_salary",
            "benefits",
            "required_skills",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 6}),
            "benefits": forms.Textarea(attrs={"rows": 3}),
            "required_skills": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # City autocomplete: browser-native filtering as the user types.
        # (We render the datalist in templates; this just binds the input to it.)
        self.fields["location"].widget = forms.TextInput(
            attrs={"placeholder": "e.g. London", "list": "uk-city-list"}
        )
        self._bootstrap()

    def clean_location(self):
        location = (self.cleaned_data.get("location") or "").strip()
        if location and location not in UK_CITIES:
            raise forms.ValidationError("Please choose a UK city from the list.")
        return location

    def clean(self):
        cleaned = super().clean()
        min_salary = cleaned.get("min_salary")
        max_salary = cleaned.get("max_salary")
        if min_salary is not None and max_salary is not None and min_salary > max_salary:
            raise forms.ValidationError("Min salary must be less than or equal to max salary.")
        return cleaned


class JobApplicationForm(_BootstrapMixin, forms.ModelForm):
    """Application form.

    We keep it lightweight: resume comes from the user's single uploaded resume
    (enforced elsewhere), and we support an optional note.

    Pass `job=` to enforce the employer's cover-letter requirement.
    """

    class Meta:
        model = JobApplication
        fields = ["cover_letter", "note"]
        widgets = {
            "cover_letter": forms.Textarea(attrs={"rows": 5}),
            "note": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, job=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.job = job
        self._bootstrap()

        # Cover letter: optional unless employer requires it.
        required = bool(getattr(job, "cover_letter_required", False))
        self.fields["cover_letter"].required = required
        self.fields["cover_letter"].widget.attrs.setdefault(
            "placeholder",
            "Write a short cover letter..." if required else "Cover letter (optional)",
        )

        self.fields["note"].required = False
        self.fields["note"].widget.attrs.setdefault("placeholder", "Add a private note (optional)")

    def clean_cover_letter(self):
        text = (self.cleaned_data.get("cover_letter") or "").strip()
        if self.fields["cover_letter"].required and not text:
            raise forms.ValidationError("This job requires a cover letter.")
        return text


class JobAlertForm(_BootstrapMixin, forms.ModelForm):
    class Meta:
        from .models import JobAlert
        model = JobAlert
        fields = ["keywords", "skills", "location", "min_salary", "max_salary", "is_enabled"]
        widgets = {"keywords": forms.TextInput(), "skills": forms.TextInput()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["location"].widget = forms.Select(
            choices=[("", "All cities")] + [(c, c) for c in ENGLAND_CITIES]
        )
        self._bootstrap()

    def clean(self):
        cleaned = super().clean()
        min_salary = cleaned.get("min_salary")
        max_salary = cleaned.get("max_salary")
        if min_salary is not None and max_salary is not None and min_salary > max_salary:
            raise forms.ValidationError("Min salary must be less than or equal to max salary.")
        return cleaned
