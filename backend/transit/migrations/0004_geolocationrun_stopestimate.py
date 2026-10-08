# Gerado pelo Django 6.0.8 em 2026-09-24 03:49

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('transit', '0003_networkmetadata_route_sourcedocument_stop_routestop_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='GeolocationRun',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('algorithm', models.CharField(max_length=80)),
                ('source_hash', models.CharField(max_length=64)),
                ('summary', models.JSONField(default=dict)),
            ],
        ),
        migrations.CreateModel(
            name='StopEstimate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('position', models.PositiveIntegerField()),
                ('status', models.CharField(default='pending', max_length=30)),
                ('lat', models.FloatField(blank=True, null=True)),
                ('lon', models.FloatField(blank=True, null=True)),
                ('evidence', models.JSONField(default=dict)),
                ('route', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='transit.route')),
                ('run', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='transit.geolocationrun')),
                ('stop', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='transit.stop')),
            ],
            options={
                'constraints': [models.UniqueConstraint(fields=('route', 'position'), name='unique_estimate_route_position')],
            },
        ),
    ]
