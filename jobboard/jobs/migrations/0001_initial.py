# Generated manually for Phase 4 (Managers are in models; migrations only create tables)
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Job",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255)),
                ("description", models.TextField()),
                ("location", models.CharField(max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("employer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="jobs", to="accounts.employerprofile")),
            ],
        ),
        migrations.CreateModel(
            name="JobApplication",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("resume", models.FileField(upload_to="resumes/")),
                ("cover_letter", models.TextField(blank=True, null=True)),
                ("submitted_at", models.DateTimeField(auto_now_add=True)),
                ("interview_date", models.DateField(blank=True, null=True)),
                ("status", models.CharField(choices=[("submitted", "Submitted"), ("interview", "Interview"), ("rejected", "Rejected")], default="submitted", max_length=20)),
                ("job", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="applications", to="jobs.job")),
                ("jobseeker", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="applications", to="accounts.jobseekerprofile")),
            ],
        ),
    ]
