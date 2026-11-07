# Gerado pelo Django 6.0.8 em 2026-09-24 03:26

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('transit', '0002_simulation'),
    ]

    operations = [
        migrations.CreateModel(
            name='NetworkMetadata',
            fields=[
                ('name', models.CharField(max_length=80, primary_key=True, serialize=False)),
                ('data', models.JSONField(default=dict)),
            ],
        ),
        migrations.CreateModel(
            name='Route',
            fields=[
                ('id', models.CharField(max_length=160, primary_key=True, serialize=False)),
                ('code', models.CharField(blank=True, max_length=80)),
                ('name', models.CharField(max_length=500)),
                ('source', models.CharField(max_length=80)),
                ('simulated', models.BooleanField(default=False)),
                ('routable', models.BooleanField(default=False)),
                ('data', models.JSONField(default=dict)),
            ],
        ),
        migrations.CreateModel(
            name='SourceDocument',
            fields=[
                ('id', models.CharField(max_length=64, primary_key=True, serialize=False)),
                ('provider', models.CharField(max_length=80)),
                ('url', models.URLField(max_length=1000)),
                ('kind', models.CharField(max_length=80)),
                ('status', models.CharField(max_length=30)),
                ('metadata', models.JSONField(default=dict)),
                ('content', models.TextField(blank=True)),
                ('imported_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='Stop',
            fields=[
                ('id', models.CharField(max_length=120, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=500)),
                ('lat', models.FloatField(blank=True, null=True)),
                ('lon', models.FloatField(blank=True, null=True)),
                ('source', models.CharField(max_length=80)),
                ('data', models.JSONField(default=dict)),
            ],
        ),
        migrations.CreateModel(
            name='RouteStop',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('position', models.PositiveIntegerField()),
                ('duration', models.PositiveIntegerField(blank=True, null=True)),
                ('segment', models.JSONField(blank=True, default=dict)),
                ('route', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sequence', to='transit.route')),
                ('stop', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='transit.stop')),
            ],
            options={
                'ordering': ['position'],
            },
        ),
        migrations.AddField(
            model_name='route',
            name='stops',
            field=models.ManyToManyField(through='transit.RouteStop', to='transit.stop'),
        ),
        migrations.AddConstraint(
            model_name='routestop',
            constraint=models.UniqueConstraint(fields=('route', 'position'), name='unique_route_position'),
        ),
    ]
