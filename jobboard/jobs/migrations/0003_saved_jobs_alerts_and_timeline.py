from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ("jobs", "0002_job_phase4_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="JobApplicationEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("submitted", "Submitted"), ("interview", "Interview"), ("rejected", "Rejected")], max_length=20)),
                ("note", models.CharField(blank=True, max_length=255, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("application", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="events", to="jobs.jobapplication")),
            ],
            options={"ordering": ["created_at"]},
        ),
        migrations.CreateModel(
            name="SavedJob",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("job", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="saved_by", to="jobs.job")),
                ("jobseeker", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="saved_jobs", to="accounts.jobseekerprofile")),
            ],
            options={"ordering": ["-created_at"], "unique_together": {("job", "jobseeker")}},
        ),
        migrations.CreateModel(
            name="JobAlert",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("keywords", models.CharField(blank=True, help_text="Keywords (title/skills).", max_length=255, null=True)),
                ("min_salary", models.PositiveIntegerField(blank=True, null=True)),
                ("max_salary", models.PositiveIntegerField(blank=True, null=True)),
                ("skills", models.CharField(blank=True, help_text="Comma separated skills.", max_length=255, null=True)),
                ("location", models.CharField(blank=True, max_length=255, null=True)),
                ("is_enabled", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("jobseeker", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="job_alerts", to="accounts.jobseekerprofile")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="JobAlertMatch",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("is_seen", models.BooleanField(default=False)),
                ("alert", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="matches", to="jobs.jobalert")),
                ("job", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="alert_matches", to="jobs.job")),
            ],
            options={"ordering": ["-created_at"], "unique_together": {("alert", "job")}},
        ),
    ]
