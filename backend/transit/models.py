from django.db import models


class Evaluation(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    scenario = models.CharField(max_length=200, blank=True)
    notes = models.TextField()


class Simulation(models.Model):
    enabled = models.BooleanField("Simulação ligada", default=True)
    running = models.BooleanField("Relógio em movimento", default=False)
    seconds = models.PositiveIntegerField("Segundos desde meia-noite", default=28800)
    speed = models.PositiveIntegerField(
        "Velocidade",
        choices=[(1, "Tempo normal"), (15, "15 vezes"), (60, "60 vezes")],
        default=15,
    )
    changed_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "controle da simulação"
        verbose_name_plural = "controle da simulação"

    def __str__(self):
        return "Simulação dos ônibus"

    def current_seconds(self, now=None):
        from django.utils import timezone

        elapsed = max(0, ((now or timezone.now()) - self.changed_at).total_seconds())
        return min(
            86399,
            (
                self.seconds + int(elapsed * self.speed)
                if self.enabled and self.running
                else self.seconds
            ),
        )

    def save(self, *args, **kwargs):
        self.pk = 1
        return super().save(*args, **kwargs)


class SourceDocument(models.Model):
    id = models.CharField(max_length=64, primary_key=True)
    provider = models.CharField(max_length=80)
    url = models.URLField(max_length=1000)
    kind = models.CharField(max_length=80)
    status = models.CharField(max_length=30)
    metadata = models.JSONField(default=dict)
    content = models.TextField(blank=True)
    imported_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.provider}: {self.url}"


class Stop(models.Model):
    id = models.CharField(max_length=120, primary_key=True)
    name = models.CharField(max_length=500)
    lat = models.FloatField(null=True, blank=True)
    lon = models.FloatField(null=True, blank=True)
    source = models.CharField(max_length=80)
    data = models.JSONField(default=dict)

    def __str__(self):
        return self.name


class Route(models.Model):
    id = models.CharField(max_length=160, primary_key=True)
    code = models.CharField(max_length=80, blank=True)
    name = models.CharField(max_length=500)
    source = models.CharField(max_length=80)
    simulated = models.BooleanField(default=False)
    routable = models.BooleanField(default=False)
    data = models.JSONField(default=dict)
    stops = models.ManyToManyField(Stop, through="RouteStop")

    def __str__(self):
        return f"{self.code} — {self.name}"


class RouteStop(models.Model):
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name="sequence")
    stop = models.ForeignKey(Stop, on_delete=models.PROTECT)
    position = models.PositiveIntegerField()
    duration = models.PositiveIntegerField(null=True, blank=True)
    segment = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["position"]
        constraints = [
            models.UniqueConstraint(
                fields=["route", "position"], name="unique_route_position"
            )
        ]


class NetworkMetadata(models.Model):
    name = models.CharField(max_length=80, primary_key=True)
    data = models.JSONField(default=dict)


class GeolocationRun(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    algorithm = models.CharField(max_length=80)
    source_hash = models.CharField(max_length=64)
    summary = models.JSONField(default=dict)


class StopEstimate(models.Model):
    route = models.ForeignKey(Route, on_delete=models.CASCADE)
    stop = models.ForeignKey(Stop, on_delete=models.CASCADE)
    position = models.PositiveIntegerField()
    run = models.ForeignKey(GeolocationRun, on_delete=models.PROTECT)
    status = models.CharField(max_length=30, default="pending")
    lat = models.FloatField(null=True, blank=True)
    lon = models.FloatField(null=True, blank=True)
    evidence = models.JSONField(default=dict)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["run", "route", "position"], name="unique_estimate_run_route_position"
            )
        ]
