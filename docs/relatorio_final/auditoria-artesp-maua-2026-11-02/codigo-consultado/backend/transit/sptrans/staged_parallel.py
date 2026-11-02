"""Isolated native engines with bounded work queue and a single SQLite writer.

Linux fork shares immutable ride/foot arrays; no SQLite connection crosses fork.
Each child owns the mutable frontier and output of its inherited native engine.
"""
from concurrent.futures import ProcessPoolExecutor, wait, FIRST_COMPLETED
import json
import gc
import multiprocessing
from pathlib import Path
import shutil
import sqlite3
import time
from django.utils import timezone
from . import staged_materialized as staged

_engine = None


def _generate(origin, units):
    started = time.monotonic()
    rows = list(_engine.rows(origin, units))
    return origin, rows, time.monotonic()-started


def build(stage, path=None, workers=32, min_free_gib=20, progress=print, origins=None):
    global _engine
    if stage not in (0, 1) or not 1 <= workers <= 32:
        raise ValueError('Etapa ou número de processos inválido.')
    path = Path(path or staged.database_path()); started=time.monotonic()
    with sqlite3.connect(path) as db:
        meta=json.loads(db.execute('SELECT value FROM metadata WHERE id=1').fetchone()[0])
        if meta['signature'] != staged.signature(meta['signature']['walks'][0]):
            raise ValueError('Fonte incompatível.')
        if stage == 1 and 0 not in meta['complete_stages']:
            raise ValueError('Conclua custo zero primeiro.')
        all_origins=[r[0] for r in db.execute('SELECT id FROM stops ORDER BY id')]
        done={r[0] for r in db.execute('SELECT origin FROM progress WHERE stage=?',(stage,))}
        todo=iter(o for o in (all_origins if origins is None else origins) if o not in done)
        _engine=staged.Engine(db)
    # sqlite's context manager commits but does not close the connection.
    db.close()
    # Avoid copying inherited Python caches when a child triggers cyclic GC.
    gc.collect()
    gc.freeze()
    pool=ProcessPoolExecutor(max_workers=workers, mp_context=multiprocessing.get_context('fork'))
    try:
        pending={}
        def submit():
            origin=next(todo,None)
            if origin is not None:
                pending[pool.submit(_generate,origin,stage*3)]=origin
        # Start every worker before opening the writer.
        for _ in range(workers): submit()
        with sqlite3.connect(path,timeout=60) as db:
            while pending:
                finished,_=wait(pending,return_when=FIRST_COMPLETED)
                # Commit ready origins together. Paths and checkpoints are atomic;
                # amortize fsync without increasing the bounded worker queue.
                completed=[]
                with db:
                    for future in finished:
                        pending.pop(future)
                        origin,rows,seconds=future.result()
                        estimate=sum(len(row[2])+32 for row in rows)*3
                        if shutil.disk_usage(path.parent).free-estimate < min_free_gib*1024**3:
                            raise OSError('Reserva mínima de disco atingida; progresso preservado.')
                        count=sum(row[2][0] for row in rows)
                        db.execute('DELETE FROM paths WHERE origin=?',(origin,))
                        db.executemany('INSERT INTO paths VALUES(?,?,?)',rows)
                        db.execute('INSERT INTO progress VALUES(?,?,?,?,?)',(stage,origin,count,len(rows),seconds))
                        completed.append(origin)
                        submit()
                for origin in completed:
                    done.add(origin)
                    if len(done)%100==0 or len(done)==len(all_origins):
                        progress(f'etapa={stage} origens={len(done)}/{len(all_origins)} banco={path.stat().st_size/1024**3:.3f}GiB livre={shutil.disk_usage(path.parent).free/1024**3:.2f}GiB')
            if len(done)==len(all_origins):
                if meta['signature']!=staged.signature(meta['signature']['walks'][0]):
                    raise ValueError('Fontes alteradas durante a geração.')
                if stage not in meta['complete_stages']:meta['complete_stages'].append(stage)
                meta['last_completed_at']=timezone.now().isoformat()
                with db:db.execute('UPDATE metadata SET value=? WHERE id=1',(json.dumps(meta),))
            counts=db.execute('SELECT count(*),sum(pairs),sum(paths),sum(seconds) FROM progress WHERE stage=?',(stage,)).fetchone()
        db.close()
    finally:
        pool.shutdown(wait=True,cancel_futures=True)
        _engine.close();_engine=None
        gc.unfreeze()
    return {'stage':stage,'complete':stage in meta['complete_stages'],'origins':counts[0],
            'pairs':counts[1],'routes':counts[2],'build_seconds':counts[3],
            'elapsed_seconds':time.monotonic()-started,'bytes':path.stat().st_size,
            'free_bytes':shutil.disk_usage(path.parent).free,'workers':workers}
