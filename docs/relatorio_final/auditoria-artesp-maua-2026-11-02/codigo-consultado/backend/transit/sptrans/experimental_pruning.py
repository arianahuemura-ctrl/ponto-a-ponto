"""Heurísticas opt-in para comparação offline, sem alterar os artefatos publicados."""
import json
import math


def distance(a,b):
    lat1,lon1,lat2,lon2=map(math.radians,(*a,*b))
    h=math.sin((lat2-lat1)/2)**2+math.cos(lat1)*math.cos(lat2)*math.sin((lon2-lon1)/2)**2
    return 12742000*math.asin(min(1,math.sqrt(h)))


def sampled_convergence(points,current,destination):
    """Preserva empates; poda apenas quando meio E fim se afastam estritamente.

    Pontos são as paradas posteriores na sequência, não o centro geográfico.
    Coordenadas ausentes impedem a poda, para não inventar ausência de conexão.
    """
    if not points or current is None or destination is None:return True
    samples=(points[(len(points)-1)//2],points[-1])
    if any(p is None for p in samples):return True
    baseline=distance(current,destination)
    return any(distance(p,destination)<=baseline+1e-6 for p in samples)


def convergence_filter(db,destination):
    stops={r[0]:(r[1],r[2]) if r[1] is not None and r[2] is not None else None
           for r in db.execute('SELECT id,lat,lon FROM graph_stop')}
    patterns={r[0]:json.loads(r[1]) for r in db.execute('SELECT id,stops FROM pattern')}
    cache={}
    stats={"sequences_checked":0,"sequences_pruned":0}
    def allows(edge):
        row=db.execute('SELECT pattern_id,boarding_index FROM ride_edge WHERE id=?',(edge,)).fetchone()
        if row is None:return True
        key=tuple(row)
        if key not in cache:
            sequence=patterns[row[0]];i=row[1]
            cache[key]=sampled_convergence([stops.get(s) for s in sequence[i+1:]],
                                           stops.get(sequence[i]),stops.get(destination))
            stats["sequences_checked"]+=1
            stats["sequences_pruned"]+=int(not cache[key])
        return cache[key]
    allows.stats=stats
    return allows
