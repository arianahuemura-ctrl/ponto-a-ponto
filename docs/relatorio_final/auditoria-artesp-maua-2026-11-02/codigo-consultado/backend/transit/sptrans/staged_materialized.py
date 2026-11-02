"""Materialização compacta municipal de custos 0 e 1, com retomada por origem."""
from collections import defaultdict
from contextlib import closing
import ctypes as ct
import hashlib
import json
import math
from pathlib import Path
import shutil
import sqlite3
import struct
import subprocess
import time
from django.conf import settings
from django.utils import timezone
from mbm import routing_config as config
from . import graph, planner, rail, store, walk_artifacts

VERSION=2


def database_path(): return store.database_path().with_suffix('.staged.sqlite3')


def walking_graph(target):
    """Inclui estações ferroviárias ausentes do antigo grafo exclusivo de ônibus."""
    source=store.database_path();stat=source.stat()
    stops,_,_=planner._network(str(source),stat.st_mtime_ns,stat.st_size,True)
    nearby=planner._nearby(str(source),stat.st_mtime_ns,stat.st_size,True)
    target=Path(target)
    if target.exists():
        with sqlite3.connect(target) as db:
            meta=json.loads(db.execute('SELECT value FROM graph_meta').fetchone()[0])
            if meta['source']==graph.fingerprint(source):return target
        raise ValueError('Grafo pedestre de outra fonte; escolha nova saída.')
    with sqlite3.connect(target) as db:
        db.executescript('CREATE TABLE graph_stop(id TEXT PRIMARY KEY,name TEXT,lat REAL,lon REAL); CREATE TABLE walk_edge(origin TEXT,destination TEXT,air_meters REAL); CREATE TABLE graph_meta(id INTEGER PRIMARY KEY,value TEXT);')
        db.executemany('INSERT INTO graph_stop VALUES(?,?,?,?)',[(sid,s['name'],s['lat'],s['lon']) for sid,s in stops.items()])
        db.executemany('INSERT INTO walk_edge VALUES(?,?,?)',((sid,other,meters) for sid,near in nearby.items() for other,meters in near if meters<=config.WALK_LIMIT_METERS))
        db.execute('INSERT INTO graph_meta VALUES(1,?)',(json.dumps({'version':graph.VERSION,'source':graph.fingerprint(source),'walking_speed_kmh':config.WALK_SPEED_KMH,'walk_radius':config.WALK_LIMIT_METERS}),))
    return target


def signature(walks):
    return {'version':VERSION,'gtfs':graph.fingerprint(store.database_path()),'walks':graph.fingerprint(walks),
            'rail_version':rail.VERSION,'walk_configuration':config.walking_signature(),'transfer_seconds':config.TRANSFER_SECONDS,
            'kernel':hashlib.sha256(Path(__file__).with_name('staged_kernel.cpp').read_bytes()).hexdigest(),
            'selection':'five_sequences_cost_then_structural_seconds','weights':[3,1]}


def prepare(walks,target=None,progress=print):
    target=Path(target or database_path());sig=signature(walks)
    if target.exists():
        with sqlite3.connect(target) as db:
            if json.loads(db.execute('SELECT value FROM metadata WHERE id=1').fetchone()[0])['signature']!=sig:
                raise ValueError('Materialização incompatível com as fontes.')
        return target
    temporary=target.with_suffix('.preparing.sqlite3')
    if temporary.exists():temporary.unlink()
    source=store.database_path();stat=source.stat()
    stops,trips,_=planner._network(str(source),stat.st_mtime_ns,stat.st_size,True)
    sids=sorted(stops);sid_index={sid:i for i,sid in enumerate(sids)}
    grouped=defaultdict(list)
    for trip in trips.values():
        if len(trip['times'])>1:
            grouped[(trip['route_id'],trip['direction_id'],tuple(t[0] for t in trip['times']))].append(trip)
    with sqlite3.connect(temporary) as db:
        db.executescript('''
            CREATE TABLE metadata(id INTEGER PRIMARY KEY,value TEXT);
            CREATE TABLE stops(id INTEGER PRIMARY KEY,sid TEXT UNIQUE NOT NULL);
            CREATE TABLE patterns(id INTEGER PRIMARY KEY,service INTEGER,rail INTEGER,wait REAL,trips TEXT);
            CREATE TABLE rides(id INTEGER PRIMARY KEY,pattern INTEGER,origin INTEGER,destination INTEGER,boarding INTEGER,alighting INTEGER,seconds REAL);
            CREATE TABLE walks(id INTEGER PRIMARY KEY,origin INTEGER,destination INTEGER,internal INTEGER,seconds REAL,meters REAL);
            CREATE TABLE paths(origin INTEGER,destination INTEGER,data BLOB NOT NULL,PRIMARY KEY(origin,destination)) WITHOUT ROWID;
            CREATE TABLE progress(stage INTEGER,origin INTEGER,paths INTEGER,pairs INTEGER,seconds REAL,PRIMARY KEY(stage,origin)) WITHOUT ROWID;
        ''')
        db.executemany('INSERT INTO stops VALUES(?,?)',enumerate(sids))
        services={};edge_id=1
        for pid,(_,variants) in enumerate(sorted(grouped.items())):
            representative=variants[0];is_rail=representative['route_type'] in rail.RAIL_TYPES
            service=(representative['route_id'],None if is_rail else representative['direction_id'])
            service_id=services.setdefault(service,len(services))
            frequencies=[freq[2] for trip in variants for freq in trip['frequencies'] if freq[2]>0]
            wait=min(frequencies)/2 if frequencies else 0
            db.execute('INSERT INTO patterns VALUES(?,?,?,?,?)',(pid,service_id,int(is_rail),wait,json.dumps([t['trip_id'] for t in variants])))
            edges=[];times=representative['times']
            for a in range(len(times)-1):
                for b in range(a+1,len(times)):
                    if times[a][0]==times[b][0]:continue
                    seconds=min(t['times'][b][1]-t['times'][a][2] for t in variants)
                    if seconds<0 or not math.isfinite(seconds):raise ValueError('Duração GTFS inválida.')
                    edges.append((edge_id,pid,sid_index[times[a][0]],sid_index[times[b][0]],a,b,seconds));edge_id+=1
            db.executemany('INSERT INTO rides VALUES(?,?,?,?,?,?,?)',edges)
            if pid%250==0:progress(f'Fonte: {pid+1} padrões, {edge_id-1} trechos')
        wid=1
        with closing(graph.readonly(walks)) as foot:
            wm=json.loads(foot.execute('SELECT value FROM walk_meta').fetchone()[0])
            if (wm['source_gtfs']!=sig['gtfs'] or wm['configuration']!=config.walking_signature()
                    or wm.get('stops')!=len(sids)):
                raise ValueError('Rede pedestre incompatível ou com cobertura incompleta de pontos/estações.')
            for row in foot.execute("SELECT origin,destination,seconds,distance_meters FROM walk_edge WHERE status='verified'"):
                a,b,seconds,meters=row
                db.execute('INSERT INTO walks VALUES(?,?,?,?,?,?)',(wid,sid_index[a],sid_index[b],0,seconds,meters));wid+=1
        for (a,b),foot in rail.internal_transfers(stops).items():
            db.execute('DELETE FROM walks WHERE origin=? AND destination=?',(sid_index[a],sid_index[b]))
            db.execute('INSERT INTO walks VALUES(?,?,?,?,?,?)',(wid,sid_index[a],sid_index[b],1,foot['seconds'],0));wid+=1
        # Compact IDs make native arrays and references deterministic.
        db.execute('CREATE TABLE ordered_walks AS SELECT ROW_NUMBER() OVER(ORDER BY id) id,origin,destination,internal,seconds,meters FROM walks')
        db.execute('DROP TABLE walks');db.execute('ALTER TABLE ordered_walks RENAME TO walks')
        db.execute('CREATE UNIQUE INDEX walks_id ON walks(id)')
        db.execute('INSERT INTO metadata VALUES(1,?)',(json.dumps({'signature':sig,'created_at':timezone.now().isoformat(),
            'complete_stages':[],'stops':len(sids),'patterns':len(grouped),'rides':edge_id-1,'walk_coverage':wm,
            'ranking':'minimum cost, then minimum scheduled ride + mean wait + verified walking; reevaluate at query time'}),))
        if db.execute('PRAGMA quick_check').fetchone()[0]!='ok':raise ValueError('Fonte inválida.')
    temporary.replace(target)
    return target


class Ride(ct.Structure):
    _fields_=[(k,ct.c_int) for k in ('id','pattern','origin','destination','boarding','alighting')]+[('seconds',ct.c_double)]
class Walk(ct.Structure):
    _fields_=[(k,ct.c_int) for k in ('id','origin','destination','internal')]+[(k,ct.c_double) for k in ('seconds','meters')]
class Pattern(ct.Structure):
    _fields_=[('service',ct.c_int),('rail',ct.c_int),('wait',ct.c_double)]


class Engine:
    def __init__(self,db,expanded=False,topup=False):
        self.max_units=12 if topup else (8 if expanded else 3)
        self.stop_count=db.execute('SELECT count(*) FROM stops').fetchone()[0]
        cpp=Path(__file__).with_name('topup_kernel.cpp' if topup else ('expanded_kernel.cpp' if expanded else 'staged_kernel.cpp'))
        digest=hashlib.sha256(cpp.read_bytes()).hexdigest()[:16]
        folder=settings.BASE_DIR/'.cache/staged-kernel';folder.mkdir(parents=True,exist_ok=True)
        library=folder/(digest+'.so')
        if not library.exists():subprocess.run(['g++','-std=c++17','-O3','-shared','-fPIC',str(cpp),'-o',str(library)],check=True)
        self.lib=ct.CDLL(str(library));self.lib.pap_engine.restype=ct.c_void_p
        self.lib.pap_engine.argtypes=[ct.POINTER(Ride),ct.c_int,ct.POINTER(Walk),ct.c_int,ct.POINTER(Pattern),ct.c_int,ct.c_int,ct.c_double]
        self.lib.pap_generate.argtypes=[ct.c_void_p,ct.c_int,ct.c_int,ct.POINTER(ct.POINTER(ct.c_ubyte)),ct.POINTER(ct.c_uint64)]
        self.lib.pap_free.argtypes=[ct.c_void_p];self.lib.pap_error.restype=ct.c_char_p
        nr=db.execute('SELECT coalesce(max(id),0)+1 FROM rides').fetchone()[0]
        nw=db.execute('SELECT coalesce(max(id),0)+1 FROM walks').fetchone()[0]
        np=db.execute('SELECT count(*) FROM patterns').fetchone()[0]
        rides=(Ride*nr)();walks=(Walk*nw)();patterns=(Pattern*np)()
        for row in db.execute('SELECT * FROM rides'):rides[row[0]]=Ride(*row)
        for row in db.execute('SELECT * FROM walks ORDER BY id'):walks[row[0]]=Walk(*row)
        for pid,service,is_rail,wait in db.execute('SELECT id,service,rail,wait FROM patterns'):patterns[pid]=Pattern(service,is_rail,wait)
        self.ptr=self.lib.pap_engine(rides,nr,walks,nw,patterns,np,self.stop_count,config.TRANSFER_SECONDS)
        if not self.ptr:raise RuntimeError(self.lib.pap_error().decode())

    def rows(self,origin,units):
        if not self.ptr or not isinstance(units,int) or not 0<=units<=self.max_units:
            raise ValueError('Motor fechado ou custo não suportado pelo gerador.')
        if not isinstance(origin,int) or not 0<=origin<self.stop_count:raise ValueError('Origem inválida.')
        data=ct.POINTER(ct.c_ubyte)();length=ct.c_uint64()
        if self.lib.pap_generate(self.ptr,origin,units,ct.byref(data),ct.byref(length)):
            raise RuntimeError(self.lib.pap_error().decode())
        result=ct.string_at(data,length.value);offset=0
        while offset<len(result):
            destination,size=struct.unpack_from('<II',result,offset);offset+=8
            yield origin,destination,result[offset:offset+size]
            offset+=size

    def close(self):
        if self.ptr:self.lib.pap_free(self.ptr);self.ptr=None

    def baseline(self,rows,completed_units=None):
        if not self.ptr or self.max_units<=3:raise ValueError('Preenchimento requer o gerador ampliado aberto.')
        if completed_units is not None:
            if self.max_units!=12:raise ValueError('Etapas incrementais requerem o gerador até quatro.')
            self.lib.pap_floor.argtypes=[ct.c_void_p,ct.c_int]
            if self.lib.pap_floor(self.ptr,completed_units):raise ValueError(self.lib.pap_error().decode())
        data=b''.join(struct.pack('<II',destination,len(blob))+blob for destination,blob in rows)
        self.lib.pap_baseline.argtypes=[ct.c_void_p,ct.c_char_p,ct.c_uint64]
        if self.lib.pap_baseline(self.ptr,data,len(data)):
            raise RuntimeError(self.lib.pap_error().decode())


def build(stage,path=None,min_free_gib=20,progress=print,origins=None):
    if stage not in (0,1):raise ValueError('Etapas autorizadas: 0 ou 1.')
    path=Path(path or database_path());started=time.monotonic()
    with sqlite3.connect(path,timeout=60) as db:
        meta=json.loads(db.execute('SELECT value FROM metadata').fetchone()[0])
        if meta['signature']!=signature(meta['signature']['walks'][0]):raise ValueError('Fontes alteradas.')
        if stage==1 and 0 not in meta['complete_stages']:raise ValueError('Conclua custo zero antes de custo um.')
        all_origins=[row[0] for row in db.execute('SELECT id FROM stops ORDER BY id')]
        todo=all_origins if origins is None else list(origins)
        done={row[0] for row in db.execute('SELECT origin FROM progress WHERE stage=?',(stage,))}
        engine=Engine(db)
        try:
            for origin in todo:
                if origin in done:continue
                if shutil.disk_usage(path.parent).free<min_free_gib*1024**3:raise OSError('Reserva mínima de disco atingida; progresso preservado.')
                before=time.monotonic();rows=list(engine.rows(origin,stage*3));count=sum(row[2][0] for row in rows)
                estimated_write_bytes=sum(len(row[2])+32 for row in rows)*3
                if shutil.disk_usage(path.parent).free-estimated_write_bytes<min_free_gib*1024**3:raise OSError('Reserva mínima de disco atingida; origem não publicada.')
                with db:
                    db.execute('DELETE FROM paths WHERE origin=?',(origin,))
                    db.executemany('INSERT INTO paths VALUES(?,?,?)',rows)
                    db.execute('INSERT INTO progress VALUES(?,?,?,?,?)',(stage,origin,count,len(rows),time.monotonic()-before))
                done.add(origin)
                if len(done)%100==0 or len(done)==len(all_origins):
                    progress(f'etapa={stage} origens={len(done)}/{len(all_origins)} ultima={time.monotonic()-before:.3f}s banco={path.stat().st_size/1024**3:.3f}GiB livre={shutil.disk_usage(path.parent).free/1024**3:.2f}GiB')
            if len(done)==len(all_origins):
                if meta['signature']!=signature(meta['signature']['walks'][0]):raise ValueError('Fontes alteradas durante a geração.')
                if stage not in meta['complete_stages']:meta['complete_stages'].append(stage)
                meta['last_completed_at']=timezone.now().isoformat()
                with db:db.execute('UPDATE metadata SET value=? WHERE id=1',(json.dumps(meta),))
            counts=db.execute('SELECT count(*),sum(pairs),sum(paths),sum(seconds) FROM progress WHERE stage=?',(stage,)).fetchone()
        finally:engine.close()
    return {'stage':stage,'complete':stage in meta['complete_stages'],'origins':counts[0],'pairs':counts[1],
            'routes':counts[2],'build_seconds':counts[3],'elapsed_seconds':time.monotonic()-started,
            'bytes':path.stat().st_size,'free_bytes':shutil.disk_usage(path.parent).free}


def decode(data):
    offset=1;result=[]
    for _ in range(data[0]):
        length,units=data[offset:offset+2];offset+=2
        access=struct.unpack_from('<I',data,offset)[0];offset+=4;legs=[]
        for i in range(length):
            edge=struct.unpack_from('<I',data,offset)[0];offset+=4
            walk=struct.unpack_from('<I',data,offset)[0] if i else access
            if i:offset+=4
            legs.append((edge,walk))
        egress=struct.unpack_from('<I',data,offset)[0];offset+=4
        result.append({'units':units,'legs':legs,'egress':egress})
    if offset!=len(data):raise ValueError('Registro materializado inválido.')
    return result
