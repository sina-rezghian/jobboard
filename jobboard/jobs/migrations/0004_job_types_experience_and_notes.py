from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("jobs", "0003_saved_jobs_alerts_and_timeline"),
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="job",
            name="job_type",
            field=models.CharField(choices=[("full_time", "Full-time"), ("part_time", "Part-time"), ("contract", "Contract"), ("intern", "Internship"), ("remote", "Remote")], default="full_time", max_length=20),
        ),
        migrations.AddField(
            model_name="job",
            name="experience_level",
            field=models.CharField(choices=[("entry", "Entry"), ("mid", "Mid"), ("senior", "Senior"), ("lead", "Lead")], default="entry", max_length=20),
        ),
        migrations.AddField(
            model_name="job",
            name="cover_letter_required",
            field=models.BooleanField(default=False, help_text="If true, applicants must provide a cover letter."),
        ),
        migrations.CreateModel(
            name="ApplicationNote",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("content", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("application", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="notes", to="jobs.jobapplication")),
                ("employer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="application_notes", to="accounts.employerprofile")),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]
