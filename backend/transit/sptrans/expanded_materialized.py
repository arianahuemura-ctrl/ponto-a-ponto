"""Preenche somente vagas dos pares, mantendo a materialização até custo 1 intacta."""
from concurrent.futures import ProcessPoolExecutor, wait, FIRST_COMPLETED
from contextlib import closing
import hashlib
import json
import multiprocessing
from pathlib import Path
import shutil
import sqlite3
import time
from django.utils import timezone
from . import staged_materialized as staged


def signature(base):
    return {'base':base,'kernel':hashlib.sha256(Path(__file__).with_name('expanded_kernel.cpp').read_bytes()).hexdigest(),
            'max_cost_units':8,'extra_over_minimum_units':3,'max_routes':5,'only_vacancies':True}


_worker_engine=None
_worker_db=None

def initialize(path):
    import django,resource
    django.setup()
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    resource.setrlimit(resource.RLIMIT_AS,(3*1024**3,3*1024**3))
    global _worker_engine,_worker_db
    _worker_db=sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True,timeout=60)
    _worker_engine=staged.Engine(_worker_db,expanded=True)


def calculate(origin):
    started=time.monotonic()
    baseline=_worker_db.execute('SELECT destination,data FROM paths WHERE origin=? ORDER BY destination',(origin,)).fetchall()
    previous={dest:data[0] for dest,data in baseline}
    _worker_engine.baseline(baseline)
    rows=list(_worker_engine.rows(origin,8))
    added=new_pairs=0
    for _,dest,data in rows:
        old=previous.get(dest,0)
        if not old<data[0]<=5:raise ValueError('Expansão alterou um par cheio ou removeu rotas.')
        added+=data[0]-old;new_pairs+=old==0
    return rows,{'new_pairs':new_pairs,'added_routes':added,'changed_pairs':len(rows),'seconds':time.monotonic()-started}


def build(path=None,workers=4,min_free_gib=20,progress=print,origins=None):
    if not 1<=workers<=8:raise ValueError('Use de um a oito processos.')
    path=Path(path or staged.database_path());started=time.monotonic()
    with closing(sqlite3.connect(path,timeout=120)) as db:
        meta=json.loads(db.execute('SELECT value FROM metadata').fetchone()[0])
        if meta['signature']!=staged.signature(meta['signature']['walks'][0]):raise ValueError('Fontes alteradas.')
        if 1 not in meta['complete_stages']:raise ValueError('Conclua primeiro a etapa de custo até 1.')
        expected=signature(meta['signature'])
        if meta.get('expanded_signature',expected)!=expected:raise ValueError('Gerador da expansão mudou; retomada cancelada.')
        db.executescript('''CREATE TABLE IF NOT EXISTS expanded_paths(origin INTEGER,destination INTEGER,data BLOB NOT NULL,
            PRIMARY KEY(origin,destination)) WITHOUT ROWID;
            CREATE TABLE IF NOT EXISTS expanded_progress(origin INTEGER PRIMARY KEY,new_pairs INTEGER,added_routes INTEGER,changed_pairs INTEGER,seconds REAL);''')
        meta['expanded_signature']=expected;meta.setdefault('expanded_started_at',timezone.now().isoformat())
        with db:db.execute('UPDATE metadata SET value=? WHERE id=1',(json.dumps(meta),))
        all_origins=[r[0] for r in db.execute('SELECT id FROM stops ORDER BY id')]
        done={r[0] for r in db.execute('SELECT origin FROM expanded_progress')}
        todo=iter(o for o in (all_origins if origins is None else origins) if o not in done)
        # Compile once before spawning to avoid concurrent publication of a shared library.
        engine=staged.Engine(db,expanded=True);engine.close()
        with ProcessPoolExecutor(max_workers=workers,mp_context=multiprocessing.get_context('spawn'),
                                 initializer=initialize,initargs=(str(path),)) as pool:
            pending={}
            def enqueue():
                origin=next(todo,None)
                if origin is not None:pending[pool.submit(calculate,origin)]=origin
            for _ in range(workers):enqueue()
            while pending:
                if shutil.disk_usage(path.parent).free<min_free_gib*1024**3:raise OSError('Reserva de disco atingida; progresso preservado.')
                ready,_=wait(pending,return_when=FIRST_COMPLETED)
                for future in ready:
                    origin=pending.pop(future);rows,stats=future.result()
                    required=3*sum(len(r[2])+32 for r in rows)
                    if shutil.disk_usage(path.parent).free-required<min_free_gib*1024**3:raise OSError('Reserva de disco atingida; origem não publicada.')
                    with db:
                        db.executemany('INSERT INTO expanded_paths VALUES(?,?,?)',rows)
                        db.execute('INSERT INTO expanded_progress VALUES(?,?,?,?,?)',(origin,stats['new_pairs'],stats['added_routes'],stats['changed_pairs'],stats['seconds']))
                    done.add(origin);enqueue()
                    if len(done)%10==0 or len(done)==len(all_origins):
                        progress(f'custo<3 origens={len(done)}/{len(all_origins)} ultima={stats["seconds"]:.2f}s banco={path.stat().st_size/1024**3:.3f}GiB livre={shutil.disk_usage(path.parent).free/1024**3:.2f}GiB')
        if len(done)==len(all_origins):
            if expected!=signature(staged.signature(meta['signature']['walks'][0])):raise ValueError('Fontes mudaram durante a geração.')
            meta['expanded_complete_units']=8;meta['expanded_completed_at']=timezone.now().isoformat()
            with db:db.execute('UPDATE metadata SET value=? WHERE id=1',(json.dumps(meta),))
        counts=db.execute('SELECT count(*),coalesce(sum(new_pairs),0),coalesce(sum(added_routes),0),coalesce(sum(changed_pairs),0) FROM expanded_progress').fetchone()
    return {'complete':len(done)==len(all_origins),'max_cost_exclusive':3,'max_cost_units':8,'only_vacancies':True,
            'origins':counts[0],'new_pairs':counts[1],'added_routes':counts[2],'changed_pairs':counts[3],
            'elapsed_seconds':time.monotonic()-started,'bytes':path.stat().st_size,'free_bytes':shutil.disk_usage(path.parent).free}
