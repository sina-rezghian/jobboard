from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
        ("jobs", "0001_initial"),
    ]

    operations = [
        migrations.AddField(model_name="job", name="job_type", field=models.CharField(choices=[("full_time", "Full-time"), ("part_time", "Part-time"), ("contract", "Contract"), ("intern", "Internship"), ("remote", "Remote")], default="full_time", max_length=20)),
        migrations.AddField(model_name="job", name="experience_level", field=models.CharField(choices=[("entry", "Entry"), ("mid", "Mid"), ("senior", "Senior"), ("lead", "Lead")], default="entry", max_length=20)),
        migrations.AddField(model_name="job", name="cover_letter_required", field=models.BooleanField(default=False, help_text="If true, applicants must provide a cover letter.")),
        migrations.AddField(model_name="job", name="min_salary", field=models.PositiveIntegerField(blank=True, null=True)),
        migrations.AddField(model_name="job", name="max_salary", field=models.PositiveIntegerField(blank=True, null=True)),
        migrations.AddField(model_name="job", name="benefits", field=models.TextField(blank=True, help_text="Benefits/perks (optional).", null=True)),
        migrations.AddField(model_name="job", name="required_skills", field=models.TextField(blank=True, help_text="Comma separated skills (e.g. Python, Django, SQL).", null=True)),
        migrations.AddField(model_name="jobapplication", name="note", field=models.TextField(blank=True, null=True)),
        migrations.CreateModel(
            name="ApplicationNote",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("content", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("application", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="notes", to="jobs.jobapplication")),
                ("employer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="application_notes", to="accounts.employerprofile")),
            ],
            options={"ordering": ["-created_at"]},
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
