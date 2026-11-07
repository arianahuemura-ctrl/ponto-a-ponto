"""Parâmetros validados; os padrões ficam no .env.example, não nos algoritmos."""
import math
import os
from .environment import load_environment

load_environment()


def number(name, kind=float, minimum=0, maximum=None, allow_zero=False):
    key = 'PAP_' + name
    try:
        value = kind(os.environ[key])
    except (KeyError, ValueError):
        raise ValueError(f'{key}: informe um número válido no .env.example ou .env.') from None
    if not math.isfinite(value) or value < minimum or (value == 0 and not allow_zero) or (maximum is not None and value > maximum):
        raise ValueError(f'{key}: valor fora do intervalo permitido.')
    return value

WALK_LIMIT_METERS = number('WALK_LIMIT_METERS', float)
WALK_SPEED_KMH = number('WALK_SPEED_KMH', float)
WALK_MAX_DISTANCE_METERS = number('WALK_MAX_DISTANCE_METERS', float)
WALK_SNAP_METERS = number('WALK_SNAP_METERS', float, allow_zero=True)
OSM_MARGIN_DEGREES = number('OSM_MARGIN_DEGREES', float)
OSRM_BUILD_JOBS = number('OSRM_BUILD_JOBS', int)
OSRM_THREADS = number('OSRM_THREADS', int)
WALK_WORKERS = number('WALK_WORKERS', int, maximum=16)
WALK_BATCH_SIZE = number('WALK_BATCH_SIZE', int)
OSRM_MAX_TABLE_SIZE = number('OSRM_MAX_TABLE_SIZE', int)
OSRM_STARTUP_SECONDS = number('OSRM_STARTUP_SECONDS', float)
WALK_REQUEST_SECONDS = number('WALK_REQUEST_SECONDS', float)
ROUTES_DIRECT = number('ROUTES_DIRECT', int, maximum=10000)
ROUTES_TWO_BUSES = number('ROUTES_TWO_BUSES', int, maximum=10000)
ROUTES_THREE_BUSES = number('ROUTES_THREE_BUSES', int, maximum=10000)
TRANSFER_SECONDS = number('TRANSFER_SECONDS', float, allow_zero=True)
INTERMEDIATE_WAIT_SECONDS = number('INTERMEDIATE_WAIT_SECONDS', float, allow_zero=True)
RESULT_LIMIT = number('RESULT_LIMIT', int)
INITIAL_REFINEMENT = number('INITIAL_REFINEMENT', int)
HORIZON_SECONDS = number('HORIZON_SECONDS', float)
ROUTE_SECONDS = number('ROUTE_SECONDS', float)
MIN_FREE_GIB = number('MIN_FREE_GIB', float, allow_zero=True)

OSRM_VERSION = os.environ['PAP_OSRM_VERSION']
OSM_PBF_URL = os.environ['PAP_OSM_PBF_URL']
if not OSRM_VERSION or not OSM_PBF_URL:
    raise ValueError('Configure PAP_OSRM_VERSION e PAP_OSM_PBF_URL.')
if WALK_BATCH_SIZE + 1 > OSRM_MAX_TABLE_SIZE:
    raise ValueError('PAP_OSRM_MAX_TABLE_SIZE deve comportar uma origem e PAP_WALK_BATCH_SIZE destinos.')
if WALK_LIMIT_METERS > WALK_MAX_DISTANCE_METERS:
    raise ValueError('PAP_WALK_LIMIT_METERS não pode exceder PAP_WALK_MAX_DISTANCE_METERS.')
if INITIAL_REFINEMENT < RESULT_LIMIT:
    raise ValueError('PAP_INITIAL_REFINEMENT deve ser pelo menos PAP_RESULT_LIMIT.')


def walking_signature():
    # Parâmetros de desempenho não invalidam distâncias já verificadas.
    return dict(max_meters=WALK_LIMIT_METERS, speed_kmh=WALK_SPEED_KMH,
                max_snap_meters=WALK_SNAP_METERS, margin_degrees=OSM_MARGIN_DEGREES,
                osrm_version=OSRM_VERSION)

MIN_BUS_RIDE_METERS = number('MIN_BUS_RIDE_METERS', float)
FINAL_WALK_LIMIT_METERS = number('FINAL_WALK_LIMIT_METERS', float)
