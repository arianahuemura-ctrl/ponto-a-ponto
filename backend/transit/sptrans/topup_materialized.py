"""Preenche vagas até custo quatro, preservando as materializações anteriores."""
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
from . import staged_materialized as staged, expanded_materialized as expanded


def signature(base):
    return {'base':base,'kernel':hashlib.sha256(Path(__file__).with_name('topup_kernel.cpp').read_bytes()).hexdigest(),
            'max_cost_units':12,'extra_over_minimum_units':3,'max_routes':5,'only_vacancies':True}


# Compatible predecessors differ only in when admissible target bounds are
# checked and in temporary exclusion-set allocation. Exhaustive fixtures and
# five real-origin byte comparisons verify equivalence; other changes fail closed.
PRE_PRUNING_KERNEL='3c429a5cdd4c8870b264e9bcd5058c0eb7e7c17164e1b87beac28c929278dd1e'
PRE_SMALLSETS_KERNEL='340bef2193605a1cbbcf21f1290acd253cb0ef7a8742d2ab69fa4e553feb7324'


def signature_matches(actual,base):
    expected=signature(base)
    return actual==expected or any(actual=={**expected,'kernel':kernel}
                                   for kernel in (PRE_PRUNING_KERNEL,PRE_SMALLSETS_KERNEL))


_worker_engine=None
_worker_db=None

def initialize(path):
    import django,resource
    django.setup()
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    resource.setrlimit(resource.RLIMIT_AS,(3*1024**3,3*1024**3))
    global _worker_engine,_worker_db
    _worker_db=sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True,timeout=60)
    _worker_engine=staged.Engine(_worker_db,topup=True)


def calculate(origin):
    started=time.monotonic()
    baseline=_worker_db.execute('SELECT destination,data FROM paths WHERE origin=? ORDER BY destination',(origin,)).fetchall()
    merged=dict(baseline)
    merged.update(_worker_db.execute('SELECT destination,data FROM expanded_paths WHERE origin=?',(origin,)))
    baseline=list(merged.items())
    previous={dest:data[0] for dest,data in baseline}
    changed={}
    for ceiling in range(9,13):
        _worker_engine.baseline(merged.items(),completed_units=ceiling-1)
        for _,dest,data in _worker_engine.rows(origin,ceiling):
            merged[dest]=data;changed[dest]=data
    rows=[(origin,dest,data) for dest,data in sorted(changed.items())]
    added=new_pairs=0
    for _,dest,data in rows:
        old=previous.get(dest,0)
        if not old<data[0]<=5:raise ValueError('Expansão alterou um par cheio ou removeu rotas.')
        added+=data[0]-old;new_pairs+=old==0
    return rows,{'new_pairs':new_pairs,'added_routes':added,'changed_pairs':len(rows),'seconds':time.monotonic()-started}


def build(path=None,workers=4,min_free_gib=20,progress=print,origins=None):
    if not 1<=workers<=16:raise ValueError('Use de um a dezesseis processos.')
    path=Path(path or staged.database_path());started=time.monotonic()
    with closing(sqlite3.connect(path,timeout=120)) as db:
        meta=json.loads(db.execute('SELECT value FROM metadata').fetchone()[0])
        if meta['signature']!=staged.signature(meta['signature']['walks'][0]):raise ValueError('Fontes alteradas.')
        if 1 not in meta['complete_stages']:raise ValueError('Conclua primeiro a etapa de custo até 1.')
        if meta.get('expanded_complete_units')!=8 or meta.get('expanded_signature')!=expanded.signature(meta['signature']):
            raise ValueError('Conclua e valide a etapa de custo menor que três.')
        expected=signature(meta['expanded_signature'])
        if not signature_matches(meta.get('topup_signature',expected),meta['expanded_signature']):
            raise ValueError('Gerador da expansão mudou; retomada cancelada.')
        db.executescript('''CREATE TABLE IF NOT EXISTS topup_paths(origin INTEGER,destination INTEGER,data BLOB NOT NULL,
            PRIMARY KEY(origin,destination)) WITHOUT ROWID;
            CREATE TABLE IF NOT EXISTS topup_progress(origin INTEGER PRIMARY KEY,new_pairs INTEGER,added_routes INTEGER,changed_pairs INTEGER,seconds REAL);''')
        meta['topup_signature']=expected;meta.setdefault('topup_started_at',timezone.now().isoformat())
        with db:db.execute('UPDATE metadata SET value=? WHERE id=1',(json.dumps(meta),))
        all_origins=[r[0] for r in db.execute('SELECT id FROM stops ORDER BY id')]
        done={r[0] for r in db.execute('SELECT origin FROM topup_progress')}
        todo=iter(o for o in (all_origins if origins is None else origins) if o not in done)
        # Compile once before spawning to avoid concurrent publication of a shared library.
        engine=staged.Engine(db,topup=True);engine.close()
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
                        db.executemany('INSERT INTO topup_paths VALUES(?,?,?)',rows)
                        db.execute('INSERT INTO topup_progress VALUES(?,?,?,?,?)',(origin,stats['new_pairs'],stats['added_routes'],stats['changed_pairs'],stats['seconds']))
                    done.add(origin);enqueue()
                    if len(done)%10==0 or len(done)==len(all_origins):
                        progress(f'custo<=4 origens={len(done)}/{len(all_origins)} ultima={stats["seconds"]:.2f}s banco={path.stat().st_size/1024**3:.3f}GiB livre={shutil.disk_usage(path.parent).free/1024**3:.2f}GiB')
        if len(done)==len(all_origins):
            if expected!=signature(expanded.signature(staged.signature(meta['signature']['walks'][0]))):raise ValueError('Fontes mudaram durante a geração.')
            meta['topup_complete_units']=12;meta['topup_completed_at']=timezone.now().isoformat()
            with db:db.execute('UPDATE metadata SET value=? WHERE id=1',(json.dumps(meta),))
        counts=db.execute('SELECT count(*),coalesce(sum(new_pairs),0),coalesce(sum(added_routes),0),coalesce(sum(changed_pairs),0) FROM topup_progress').fetchone()
    return {'complete':len(done)==len(all_origins),'max_cost_inclusive':4,'max_cost_units':12,'only_vacancies':True,
            'origins':counts[0],'new_pairs':counts[1],'added_routes':counts[2],'changed_pairs':counts[3],
            'elapsed_seconds':time.monotonic()-started,'bytes':path.stat().st_size,'free_bytes':shutil.disk_usage(path.parent).free}
