"""Eventos estruturados, sem texto livre; armazenamento separado do banco do PaP."""
import json
import math
import os
from pathlib import Path
import sqlite3
import time
import uuid
from django.conf import settings
from django.core import signing
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.http import require_http_methods

from scripts.telemetry_storage import setup, encode, collect

SALT = 'pap-usability-v1'
SCHEMA = {
    'feedback': {'payload': str},
    'trace': {'payload': str},
    'session_start': {'width': (0, 10000), 'height': (0, 10000)},
    'state': {'mode': {'origin','destination','board','map','watch'}, 'view': {'navigate','favorites','more'}, 'origin': bool, 'destination': bool, 'gps': bool},
    'action': {'target': {'origin','destination','favorite','cancel','route','search','lamp','map_point'}},
    'api': {'endpoint': {'board','trips','stops','destination','addresses','walk','other'}, 'status': (0,599), 'ms': (0,3600000)},
    'error': {'kind': {'uncaught','promise'}},
    'dimmer': {'phase': {'open','commit','cancel'}, 'value': (0,100)},
}


def validate_trace(value):
    if not isinstance(value,dict) or not isinstance(value.get('kind'),str):raise ValueError()
    if value['kind']=='chunk':
        if set(value)!={'kind','id','index','total','text'}:raise ValueError()
        if not isinstance(value['id'],str) or not 1<=len(value['id'])<=64:raise ValueError()
        if type(value['total']) is not int or not 1<=value['total']<=2048:raise ValueError()
        if type(value['index']) is not int or not 0<=value['index']<value['total']:raise ValueError()
        if not isinstance(value['text'],str) or len(value['text'])>8000:raise ValueError()
    else:
        if not 1<=len(value['kind'])<=64 or not isinstance(value.get('details'),dict):raise ValueError()
        if value['kind']=='visual':
            event=value['details']
            if type(event.get('type')) is not int or event['type'] not in range(7):raise ValueError()
            if not isinstance(event.get('data'),dict):raise ValueError()
            timestamp=event.get('timestamp')
            if type(timestamp) not in (int,float) or not math.isfinite(timestamp) or timestamp<0:raise ValueError()
    return value


def validate(events):
    if not isinstance(events,list) or not 1 <= len(events) <= 20:
        raise ValueError()
    clean=[]
    for event in events:
        if not isinstance(event,dict) or set(event) != {'type','data','seq'}:
            raise ValueError()
        kind=event['type']; data=event['data']; seq=event['seq']
        if kind not in SCHEMA or not isinstance(data,dict) or set(data) != set(SCHEMA[kind]) or type(seq) is not int or not 0 <= seq <= 1000000:
            raise ValueError()
        for key,value in data.items():
            rule=SCHEMA[kind][key]
            if rule is str:
                if not isinstance(value,str) or len(value)>12000: raise ValueError()
                json.loads(value)
            elif rule is bool:
                if type(value) is not bool: raise ValueError()
            elif isinstance(rule,tuple):
                if type(value) is not int or not rule[0] <= value <= rule[1]: raise ValueError()
            elif not isinstance(value,str) or value not in rule: raise ValueError()
        if kind=='trace':validate_trace(json.loads(data['payload']))
        if kind=='feedback':
            feedback=json.loads(data['payload'])
            if not isinstance(feedback,dict) or set(feedback)!={'category','message','at','elapsed'}:raise ValueError()
            if feedback['category'] not in ['problema','sugestao','elogio']:raise ValueError()
            if not isinstance(feedback['message'],str) or not 1<=len(feedback['message'].strip())<=2000:raise ValueError()
            from datetime import datetime
            if not isinstance(feedback['at'],str):raise ValueError()
            datetime.fromisoformat(feedback['at'].replace('Z','+00:00'))
            if type(feedback['elapsed']) not in (int,float) or not 0<=feedback['elapsed']<=86400000:raise ValueError()
        clean.append((seq,kind,json.dumps(data,separators=(',',':'))))
    return clean


def connection():
    path=Path(getattr(settings,'PAP_USABILITY_DB',Path.home()/'.local/state/pap/usability/events.sqlite3'))
    path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    fd=os.open(path,os.O_CREAT|os.O_WRONLY,0o600);os.close(fd)
    db=sqlite3.connect(path,timeout=3)
    db.execute('CREATE TABLE IF NOT EXISTS events (session TEXT,seq INTEGER,received REAL,type TEXT,data TEXT,PRIMARY KEY(session,seq))')
    db.execute('CREATE INDEX IF NOT EXISTS events_received ON events(received)')
    setup(db)
    return db


@require_http_methods(['GET','POST'])
def events(request):
    if request.method=='GET':
        token=request.headers.get('X-Pap-Session','')
        try: session=signing.loads(token,salt=SALT,max_age=43200)
        except signing.BadSignature:
            session=str(uuid.uuid4());token=signing.dumps(session,salt=SALT)
        from .research import PROOF_SALT
        response=JsonResponse({'session':session,'token':token,'csrf':get_token(request),'deletion_proof':signing.dumps(session,salt=PROOF_SALT)})
        response['Cache-Control']='no-store'
        return response
    if len(request.body)>262144:return JsonResponse({'error':'Lote muito grande.'},status=413)
    try:
        payload=json.loads(request.body)
        if not isinstance(payload,dict) or set(payload)!={'token','events'}:raise ValueError()
        session=signing.loads(payload['token'],salt=SALT,max_age=43200)
        rows=validate(payload['events'])
    except (ValueError,TypeError,KeyError,RecursionError,signing.BadSignature):
        return JsonResponse({'error':'Eventos ou sessão inválidos.'},status=400)
    now=time.time()
    db=connection()
    try:
        with db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('DELETE FROM events WHERE received < ?',(now-30*86400,))
            collect(db)
            count=db.execute('SELECT COUNT(*) FROM events WHERE session=? AND received>?',(session,now-60)).fetchone()[0]
            if count+len(rows)>3000:return JsonResponse({'error':'Limite de eventos.'},status=429)
            total,size=db.execute('SELECT COUNT(*),COALESCE(SUM(telemetry_raw_size(data)),0) FROM events').fetchone()
            recent,volume=db.execute('SELECT COUNT(*),COALESCE(SUM(telemetry_raw_size(data)),0) FROM events WHERE received>?',(now-60,)).fetchone()
            incoming=sum(len(row[2].encode()) for row in rows)
            if recent+len(rows)>getattr(settings,'PAP_TELEMETRY_EVENTS_PER_MINUTE',12000) or volume+incoming>getattr(settings,'PAP_TELEMETRY_BYTES_PER_MINUTE',32*1024*1024):
                return JsonResponse({'error':'Limite global temporário.'},status=429,headers={'Retry-After':'60'})
            if total+len(rows)>getattr(settings,'PAP_TELEMETRY_MAX_EVENTS',50000) or size+incoming>getattr(settings,'PAP_TELEMETRY_MAX_BYTES',256*1024*1024):
                return JsonResponse({'error':'Armazenamento de pesquisa cheio.'},status=503,headers={'Retry-After':'300'})
            for seq,kind,data in rows:
                if db.execute('SELECT 1 FROM events WHERE session=? AND seq=?',(session,seq)).fetchone():continue
                db.execute('INSERT INTO events VALUES (?,?,?,?,?)',(session,seq,now,kind,encode(db,session,data)))

        return JsonResponse({'accepted':len(rows),'session':session})
    finally:db.close()
