"""Voluntary messages: independent of telemetry and inaccessible to public readers."""
import hashlib
import json
import os
import sqlite3
import time
import uuid
from pathlib import Path
from django.conf import settings
from django.core import signing
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.http import require_http_methods
from django.contrib import admin
from django.shortcuts import render

PROOF_SALT='pap-research-deletion-proof-v1'

def path():
    return Path(getattr(settings,'PAP_RESEARCH_DB',Path.home()/'.local/state/pap/research/messages.sqlite3'))

def connect():
    p=path();p.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    fd=os.open(p,os.O_CREAT|os.O_WRONLY,0o600);os.close(fd)
    db=sqlite3.connect(p,timeout=3)
    db.execute('CREATE TABLE IF NOT EXISTS messages (id TEXT PRIMARY KEY, created REAL, kind TEXT, data TEXT, digest TEXT, resolved REAL)')
    return db

@require_http_methods(['GET'])
def info(request):
    response=JsonResponse({'csrf':get_token(request),'contact':getattr(settings,'PAP_RESEARCH_CONTACT','')})
    response['Cache-Control']='no-store';return response

def text(value,minimum=0):
    if not isinstance(value,str) or not minimum<=len(value.strip())<=2000:raise ValueError()
    return value.strip()

def save_message(identifier,kind,data):
    serialized=json.dumps(data,ensure_ascii=False,sort_keys=True,separators=(',',':'))
    digest=hashlib.sha256((kind+serialized).encode()).hexdigest()
    db=connect()
    try:
        with db:
            db.execute('BEGIN IMMEDIATE')
            existing=db.execute('SELECT digest FROM messages WHERE id=?',(identifier,)).fetchone()
            if existing:
                if existing[0]!=digest:return JsonResponse({'error':'Identificador já utilizado.'},status=409)
                return JsonResponse({'receipt':identifier,**({'linked':bool(data.get('session'))} if kind=='feedback' else {})})
            now=time.time()
            if db.execute('SELECT COUNT(*) FROM messages WHERE created>?',(now-60,)).fetchone()[0]>=getattr(settings,'PAP_RESEARCH_MESSAGES_PER_MINUTE',30):
                return JsonResponse({'error':'Muitas solicitações. Tente novamente mais tarde.'},status=429,headers={'Retry-After':'60'})
            if db.execute('SELECT COUNT(*) FROM messages').fetchone()[0]>=getattr(settings,'PAP_RESEARCH_MAX_MESSAGES',10000):
                return JsonResponse({'error':'Canal temporariamente indisponível.'},status=503)
            db.execute('INSERT INTO messages VALUES (?,?,?,?,?,NULL)',(identifier,now,kind,serialized,digest))
        return JsonResponse({'receipt':identifier,**({'linked':bool(data.get('session'))} if kind=='feedback' else {})},status=201)
    finally:db.close()

def body(request):
    if len(request.body)>65536:raise ValueError()
    data=json.loads(request.body)
    if not isinstance(data,dict):raise ValueError()
    if not isinstance(data.get('id'),str):raise ValueError()
    identifier=str(uuid.UUID(data['id']))
    return identifier,data

@require_http_methods(['POST'])
def feedback(request):
    try:
        identifier,data=body(request)
        if set(data) not in ({'id','category','message'},{'id','category','message','token'}):raise ValueError()
        if data['category'] not in ('problema','sugestao','elogio'):raise ValueError()
        session=None
        if 'token' in data:
            if not isinstance(data['token'],str) or len(data['token'])>512:raise ValueError()
            from .usability import SALT
            session=str(uuid.UUID(signing.loads(data['token'],salt=SALT,max_age=43200)))
        return save_message(identifier,'feedback',{'category':data['category'],'message':text(data['message'],1),'session':session})
    except (ValueError,TypeError,KeyError,signing.BadSignature):return JsonResponse({'error':'Relato inválido.'},status=400)
    except (sqlite3.Error,OSError):return JsonResponse({'error':'Canal temporariamente indisponível.'},status=503)

@require_http_methods(['POST'])
def requests(request):
    try:
        identifier,data=body(request)
        if set(data)!={'id','kind','message','proofs'} or data['kind'] not in ('contact','deletion'):raise ValueError()
        proofs=data['proofs']
        if not isinstance(proofs,list) or len(proofs)>50 or any(not isinstance(p,str) or len(p)>512 for p in proofs):raise ValueError()
        sessions=sorted({str(uuid.UUID(signing.loads(p,salt=PROOF_SALT))) for p in proofs})
        return save_message(identifier,data['kind'],{'message':text(data['message'],1),'sessions':sessions})
    except (ValueError,TypeError,KeyError,signing.BadSignature):return JsonResponse({'error':'Solicitação inválida.'},status=400)
    except (sqlite3.Error,OSError):return JsonResponse({'error':'Canal temporariamente indisponível.'},status=503)

@admin.site.admin_view
@require_http_methods(['GET','POST'])
def inbox(request):
    rows=[]
    if path().exists():
        db=connect()
        try:
            if request.method=='POST':
                if request.POST.get('confirm')!='yes':return JsonResponse({'error':'Confirmação necessária.'},status=400)
                try:identifier=str(uuid.UUID(request.POST['id']))
                except (ValueError,KeyError):return JsonResponse({'error':'Identificador inválido.'},status=400)
                with db:
                    if request.POST.get('action')=='delete':db.execute('DELETE FROM messages WHERE id=?',(identifier,))
                    else:db.execute('UPDATE messages SET resolved=? WHERE id=?',(time.time(),identifier))
            for identifier,created,kind,data,_,resolved in db.execute('SELECT * FROM messages ORDER BY created DESC LIMIT 200'):
                payload=json.loads(data);rows.append({'id':identifier,'kind':kind,'message':payload['message'],'session':payload.get('session'),'sessions':payload.get('sessions',[]),'resolved':bool(resolved)})
        finally:db.close()
    return render(request,'transit/research_inbox.html',{**admin.site.each_context(request),'title':'Feedback voluntário e solicitações de pesquisa','rows':rows})


def linked_feedback(session):
    if not path().exists():return []
    db=sqlite3.connect(path().as_uri()+'?mode=ro',uri=True)
    try:
        return [(created,json.loads(data)) for created,data in db.execute("SELECT created,data FROM messages WHERE kind='feedback' ORDER BY created") if json.loads(data).get('session')==str(session)]
    finally:db.close()
