"""Contrato de resposta da aplicação para o planejador opcional de conexões persistidas."""
import json
from . import graph, planner, store, walking


def prepare(db, origin, destination):
    from . import materialized_adapter
    return materialized_adapter.prepare(db, origin, destination)


def journey(db,result):
    legs=[];walks=[]
    for leg in result['legs']:
        departure=graph.timezone.datetime.fromtimestamp(leg['departure_s'],graph.timezone.get_current_timezone()).isoformat()
        arrival=graph.timezone.datetime.fromtimestamp(leg['arrival_s'],graph.timezone.get_current_timezone()).isoformat()
        stops=[store.stop(r) for r in db.execute('''SELECT s.* FROM stop_times st JOIN stops s USING(stop_id)
            WHERE trip_id=? ORDER BY stop_sequence''',(leg['trip_id'],))]
        a,b=leg['boarding_index'],leg['alighting_index']
        legs.append({**{k:v for k,v in leg.items() if not k.endswith('_s')},
            'origin':store.get_stop(db,leg['origin']),'destination':store.get_stop(db,leg['destination']),
            'departure':departure,'arrival':arrival,'direction_id':leg['direction'],
            'wait_minutes':round(leg['wait_seconds']/60,1),'ride_minutes':round(leg['ride_seconds']/60,1),
            'geometry':planner.leg_shape(leg['trip_id'],a,b),'stops':stops[a:b+1],'color':'#005cec'})
    for walk in result['walks']:
        walks.append({**walk,'origin':store.get_stop(db,walk['origin']),
            'destination':store.get_stop(db,walk['destination']),'geometry':json.loads(walk['geometry']) if isinstance(walk['geometry'], str) else walk['geometry'],
            'accessType':'transfer','available':True,'duration_minutes':round(walk['seconds']/60,1)})
    return {**result,'duration_minutes':round(result['duration_seconds']/60,1),
            'walking_meters':round(result['walk_meters']),
            'walking_minutes':round(result['walking_seconds']/60,1),'legs':legs,'walks':walks,'transfer_walks':walks}


def progressive(db, origin, destination, max_transfers, now, context):
    from . import materialized_adapter
    yield from materialized_adapter.progressive(db, origin, destination, max_transfers, now, context)
