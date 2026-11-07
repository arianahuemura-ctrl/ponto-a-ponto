# Gerado pelo Django 6.0.8 em 2026-09-24 02:32

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("transit", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Simulation",
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
                (
                    "enabled",
                    models.BooleanField(default=True, verbose_name="Simulação ligada"),
                ),
                (
                    "running",
                    models.BooleanField(
                        default=False, verbose_name="Relógio em movimento"
                    ),
                ),
                (
                    "seconds",
                    models.PositiveIntegerField(
                        default=28800, verbose_name="Segundos desde meia-noite"
                    ),
                ),
                (
                    "speed",
                    models.PositiveIntegerField(
                        choices=[
                            (1, "Tempo normal"),
                            (15, "15 vezes"),
                            (60, "60 vezes"),
                        ],
                        default=15,
                        verbose_name="Velocidade",
                    ),
                ),
                ("changed_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "controle da simulação",
                "verbose_name_plural": "controle da simulação",
            },
        ),
    ]
