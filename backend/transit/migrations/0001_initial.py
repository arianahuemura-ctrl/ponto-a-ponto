# Gerado pelo Django 6.0.8 em 2026-09-24 01:58

from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Evaluation",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("scenario", models.CharField(blank=True, max_length=200)),
                ("notes", models.TextField()),
            ],
        ),
    ]
