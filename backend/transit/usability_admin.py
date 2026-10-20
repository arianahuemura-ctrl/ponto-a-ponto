"""Leitura administrativa autenticada da telemetria; nunca cria o banco."""
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from django.conf import settings
from django.contrib import admin
from django.http import FileResponse, Http404
from django.shortcuts import render
from scripts.export_replay import reconstruct


def connect():
    path=Path(getattr(settings,'PAP_USABILITY_DB',Path.home()/'.local/state/pap/usability/events.sqlite3'))
    if not path.exists():return None
    return sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)


def rows_for(session):
    db=connect()
    if db is None:raise Http404('Sessão não encontrada')
    try:rows=db.execute('SELECT seq,received,type,data FROM events WHERE session=? ORDER BY seq',(str(session),)).fetchall()
    finally:db.close()
    if not rows:raise Http404('Sessão não encontrada')
    return rows


def dt(value):return datetime.fromtimestamp(value,timezone.utc)


@admin.site.admin_view
def sessions(request):
    try:page=max(1,int(request.GET.get('page',1)))
    except ValueError:page=1
    items=[];total=0;db=connect()
    if db is not None:
        try:
            total=db.execute('SELECT COUNT(DISTINCT session) FROM events').fetchone()[0]
            for session,count,start,end,size in db.execute('SELECT session,COUNT(*),MIN(received),MAX(received),SUM(LENGTH(CAST(data AS BLOB))) FROM events GROUP BY session ORDER BY MAX(received) DESC LIMIT 25 OFFSET ?',((page-1)*25,)):
                # Visual may be fragmented, so identify presence using the initial fragment as well.
                visual=db.execute("SELECT 1 FROM events WHERE session=? AND type='trace' AND (data LIKE ? OR data LIKE ?) LIMIT 1",(session,'%visual%','%rrweb%')).fetchone() is not None
                items.append(dict(id=session,count=count,start=dt(start),end=dt(end),duration=round(end-start,1),size=size,visual=visual))
        finally:db.close()
    return render(request,'transit/usability_sessions.html',dict(admin.site.each_context(request),title='Navegações por sessão',sessions=items,total=total,page=page,previous=page-1,next=page+1,has_next=page*25<total))


@admin.site.admin_view
def detail(request,session):
    rows=rows_for(session);events,incomplete=reconstruct(rows)
    seqs={r[0] for r in rows};missing=len(set(range(1,rows[-1][0]+1))-seqs)
    device=next((e['details'] for e in reversed(events) if e['kind']=='device'),{})
    viewport=next((e['details'] for e in events if e['kind']=='session_start'),{})
    device_rows=[(key,json.dumps(value,ensure_ascii=False) if isinstance(value,(dict,list)) else str(value)) for key,value in device.items()]
    visual=[e['details'] for e in events if e['kind']=='visual']
    duration=round((visual[-1]['timestamp']-visual[0]['timestamp'])/1000,1) if len(visual)>1 else None
    feedbacks=[]
    start_time=visual[0]['timestamp'] if visual else None
    for e in events:
        if e['kind']!='feedback':continue
        data=json.loads(e['details']['payload'])
        instant=datetime.fromisoformat(data['at'].replace('Z','+00:00'))
        offset=max(0,int(instant.timestamp()*1000-start_time)) if start_time is not None else None
        feedbacks.append(dict(data,instant=instant,offset=offset))
    timeline=[]
    for e in events:
        if e['kind']=='visual':continue
        timeline.append(dict(seq=e['seq'],kind=e['kind'],at=e.get('at') or e.get('received'),data=json.dumps(e['details'],ensure_ascii=False,indent=2)))
    return render(request,'transit/usability_detail.html',dict(admin.site.each_context(request),title='Detalhes da navegação',session=str(session),start=dt(rows[0][1]),end=dt(rows[-1][1]),count=len(rows),missing=missing,incomplete=len(incomplete),visual_count=len(visual),duration=duration,device_rows=device_rows,viewport=viewport,timeline=timeline,feedbacks=feedbacks))


@admin.site.admin_view
def player(request,session):
    events,_=reconstruct(rows_for(session));visual=[e['details'] for e in events if e['kind']=='visual']
    response=render(request,'transit/usability_player.html',{'events':visual})
    response['Content-Security-Policy']="default-src 'none'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob: https:; font-src 'self' data: https:; frame-src 'self' blob:; connect-src 'none'"
    response['Referrer-Policy']='strict-origin-when-cross-origin'
    return response


@admin.site.admin_view
def asset(request,name):
    files={'player.js':'rrweb-player.umd.cjs','player.css':'style.css'}
    if name=='replay-theme.js':
        return FileResponse((Path(__file__).parent/'static/transit/replay-theme.js').open('rb'),content_type='text/javascript')
    if name not in files:raise Http404()
    path=settings.BASE_DIR/'frontend/node_modules/rrweb-player/dist'/files[name]
    if not path.is_file():raise Http404('Instale as dependências do frontend')
    return FileResponse(path.open('rb'),content_type='text/javascript' if name.endswith('.js') else 'text/css')
