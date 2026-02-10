# Generated for Phase 4 enhancements
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("jobs", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="job",
            name="benefits",
            field=models.TextField(blank=True, help_text="Benefits/perks (optional).", null=True),
        ),
        migrations.AddField(
            model_name="job",
            name="max_salary",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="job",
            name="min_salary",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="job",
            name="required_skills",
            field=models.TextField(blank=True, help_text="Comma separated skills (e.g. Python, Django, SQL).", null=True),
        ),
    ]
