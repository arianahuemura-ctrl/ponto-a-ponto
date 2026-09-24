from .models import Simulation


def status():
    configuration, _ = Simulation.objects.get_or_create(pk=1)
    return {
        "enabled": configuration.enabled,
        "at": configuration.current_seconds(),
        "mode": "simulation" if configuration.enabled else "unavailable",
    }
