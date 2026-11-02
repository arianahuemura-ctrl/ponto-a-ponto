"""Read preserved materializations alongside a newer combined catalogue."""
from pathlib import Path
from django.conf import settings
from . import store, staged_adapter


def configured_path():
    value = getattr(settings, 'SPTRANS_LEGACY_DATABASE', '')
    if not value:
        return None
    path = Path(value).resolve()
    return path if path != store.database_path().resolve() else None


def progressive(path, origin, destination, max_transfers, now):
    from .alternatives import geographic_anchor
    with store.using_database(path), store.connection() as db:
        # A new ARTESP ID has no equivalent in the preserved catalogue. Do not
        # infer one from its numeric suffix or force a distant access point.
        for point in (origin, destination):
            if not geographic_anchor(point) and not db.execute(
                    'SELECT 1 FROM stops WHERE stop_id=?', (point['id'],)).fetchone():
                yield {'journeys': [], 'complete': True}
                return
        yield from staged_adapter.progressive(db, origin, destination, max_transfers, now)
