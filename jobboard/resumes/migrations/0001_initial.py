from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Resume",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("file", models.FileField(upload_to="resumes/")),
                ("title", models.CharField(blank=True, max_length=200)),
                ("education", models.CharField(blank=True, max_length=255, null=True)),
                ("skills", models.TextField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("jobseeker", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="resumes", to="accounts.jobseekerprofile")),
            ],
        ),
    ]
