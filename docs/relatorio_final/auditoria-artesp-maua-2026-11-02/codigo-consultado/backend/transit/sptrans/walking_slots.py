"""Keep stage-zero walking alternatives when filling the five slots at cost one."""
from collections import defaultdict
import json
from pathlib import Path
import sqlite3
import time
from . import staged_materialized as staged, short_walks


def first_routes(blob, limit):
    if blob[0] <= limit:
        return blob
    offset=1
    for _ in range(limit):
        legs=blob[offset]
        offset+=14+8*(legs-1)
    result=bytes([limit])+blob[1:offset]
    staged.decode(result)
    return result


def reserve(path=None, progress=print, min_free_gib=25):
    """Reconstruct stage-zero slots deterministically; safe to resume per origin.

    A walk is eligible only where the zero stage had fewer than five transport
    alternatives. Never displace an already-full set of direct services.
    """
    path=Path(path or staged.database_path());started=time.monotonic()
    with sqlite3.connect(path,timeout=60) as db:
        meta=json.loads(db.execute('SELECT value FROM metadata').fetchone()[0])
        if meta['signature']!=staged.signature(meta['signature']['walks'][0]) or meta.get('complete_stages')!=[0,1]:
            raise ValueError('Reserva requer etapas zero e um completas e fontes válidas.')
        if meta.get('expanded_signature') or meta.get('topup_signature'):
            raise ValueError('Não alterar complementações acima de custo um.')
        ids=dict(db.execute('SELECT sid,id FROM stops')); candidates=defaultdict(set)
        with sqlite3.connect(Path(meta['signature']['walks'][0]).resolve().as_uri()+'?mode=ro',uri=True) as foot:
            for a,b in foot.execute("SELECT origin,destination FROM walk_edge WHERE status='verified' AND distance_meters<=300 AND origin<>destination"):
                if a in ids and b in ids:candidates[ids[a]].add(ids[b])
        db.executescript('''CREATE TABLE IF NOT EXISTS walking_slot_reservations(origin INTEGER,destination INTEGER,zero_routes INTEGER,PRIMARY KEY(origin,destination)) WITHOUT ROWID;
            CREATE TABLE IF NOT EXISTS walking_slot_progress(origin INTEGER PRIMARY KEY,trimmed INTEGER);''')
        if not meta.get('walking_slots_complete'):
            # Invalidate the old derived table before changing transport slots.
            with db:
                db.execute('DROP TABLE IF EXISTS short_walk_paths')
                for k in list(meta):
                    if k.startswith('short_walk_'):del meta[k]
                db.execute('UPDATE metadata SET value=?',(json.dumps(meta),))
            done={r[0] for r in db.execute('SELECT origin FROM walking_slot_progress')}
            engine=staged.Engine(db)
            try:
                for i,(origin,destinations) in enumerate(sorted(candidates.items())):
                    if origin in done:continue
                    direct={b:blob[0] for _,b,blob in engine.rows(origin,0) if b in destinations}
                    trimmed=0
                    for dest in sorted(destinations):
                        n=direct.get(dest,0)
                        if n>=5:continue
                        db.execute('INSERT INTO walking_slot_reservations VALUES(?,?,?)',(origin,dest,n))
                        row=db.execute('SELECT data FROM paths WHERE origin=? AND destination=?',(origin,dest)).fetchone()
                        if row and row[0][0]>4:
                            db.execute('UPDATE paths SET data=? WHERE origin=? AND destination=?',(first_routes(row[0],4),origin,dest));trimmed+=1
                    db.execute('UPDATE progress SET paths=paths-? WHERE stage=1 AND origin=?',(trimmed,origin))
                    db.execute('INSERT INTO walking_slot_progress VALUES(?,?)',(origin,trimmed))
                    if (i+1)%128==0:db.commit()
                    if i%2000==0:progress(f'Vagas pedestres: {i+1}/{len(candidates)} origens')
                db.commit()
            finally:engine.close()
            meta['walking_slots_complete']=True
            with db:db.execute('UPDATE metadata SET value=?',(json.dumps(meta),))
        count=db.execute('SELECT count(*) FROM walking_slot_reservations').fetchone()[0]
        trimmed=db.execute('SELECT coalesce(sum(trimmed),0) FROM walking_slot_progress').fetchone()[0]
    walks=short_walks.build(path,min_free_gib=min_free_gib)
    with sqlite3.connect(path) as db:
        missing=db.execute('SELECT count(*) FROM walking_slot_reservations r WHERE NOT EXISTS (SELECT 1 FROM short_walk_paths w WHERE w.origin=r.origin AND w.destination=r.destination)').fetchone()[0]
        assert missing==0,missing
    return {'reserved_stage_zero_walks':count,'transport_alternatives_replaced':trimmed,'walking':walks,'seconds':time.monotonic()-started}
