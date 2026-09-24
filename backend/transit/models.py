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
            self.seconds + int(elapsed * self.speed)
            if self.enabled and self.running
            else self.seconds,
        )

    def save(self, *args, **kwargs):
        self.pk = 1
        return super().save(*args, **kwargs)
