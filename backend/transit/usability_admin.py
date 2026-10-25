"""Leitura administrativa autenticada da telemetria; nunca cria o banco."""
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from django.conf import settings
from django.contrib import admin
from django.http import FileResponse, Http404, JsonResponse, HttpResponseNotAllowed
from django.shortcuts import render, redirect
from scripts.export_replay import reconstruct
from scripts.telemetry_storage import read_rows, block_size, collect, decode


def connect():
    path=Path(getattr(settings,'PAP_USABILITY_DB',Path.home()/'.local/state/pap/usability/events.sqlite3'))
    if not path.exists():return None
    return sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)


def rows_for(session):
    db=connect()
    if db is None:raise Http404('Sessão não encontrada')
    try:rows=read_rows(db,str(session))
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
                visual=any('visual' in (text:=decode(db,session,data)) or 'rrweb' in text for (data,) in db.execute("SELECT data FROM events WHERE session=? AND type='trace' ORDER BY seq",(session,)))
                size+=block_size(db,session)
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
    from .research import linked_feedback
    for received,data in linked_feedback(session):
        offset=max(0,int(received*1000-start_time)) if start_time is not None else None
        feedbacks.append(dict(data,instant=dt(received),offset=offset))
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


@admin.site.admin_view
def delete_session(request,session):
    if request.method not in {'GET','POST'}:return HttpResponseNotAllowed(['GET','POST'])
    rows=rows_for(session)
    if request.method=='POST':
        if request.POST.get('confirm')!='yes':return JsonResponse({'error':'Confirmação necessária.'},status=400)
        path=Path(getattr(settings,'PAP_USABILITY_DB',Path.home()/'.local/state/pap/usability/events.sqlite3'))
        with sqlite3.connect(path.as_uri()+'?mode=rw',uri=True,timeout=3) as db:
            db.execute('DELETE FROM events WHERE session=?',(str(session),))
            collect(db)
        import shutil
        from .replay_video import cache_dir
        shutil.rmtree(cache_dir(session),ignore_errors=True)
        return redirect('usability-sessions')
    return render(request,'transit/usability_delete.html',dict(admin.site.each_context(request),title='Apagar navegação',session=str(session),count=len(rows)))


@admin.site.admin_view
def export_json(request,session):
    if request.method!='GET':return HttpResponseNotAllowed(['GET'])
    from .replay_video import cache_dir, revision
    import fcntl
    import os
    rows=rows_for(session)
    folder=cache_dir(session);output=folder/(revision(rows)+'.json')
    with (folder/'json.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        if not output.exists():
            events,problems=reconstruct(rows)
            data={'version':1,'session':str(session),'events':events,'reconstruction_problems':problems,
                'records':[{'seq':seq,'received':received,'type':kind,'data':json.loads(data)} for seq,received,kind,data in rows]}
            temporary=output.with_suffix('.tmp')
            temporary.write_text(json.dumps(data,ensure_ascii=False));os.chmod(temporary,0o600)
            os.replace(temporary,output)
    return FileResponse(output.open('rb'),as_attachment=True,filename=f'pap-navegacao-{session}.json',content_type='application/json')


@admin.site.admin_view
def export_video(request,session):
    from . import replay_video
    owner=(str(request.user.pk),str(session))
    if request.method=='POST':
        rows=rows_for(session)
        key=replay_video.revision(rows)
        token=replay_video.token_for(owner,key)
        existing=replay_video.get(token,owner)
        if existing and existing['state'] in {'running','ready'}:return JsonResponse({'job':token},status=202)
        events,problems=reconstruct(rows)
        visual=[e['details'] for e in events if e['kind']=='visual']
        if len(visual)<2 or not any(e['type']==2 for e in visual):
            return JsonResponse({'error':'Sessão sem replay visual suficiente.'},status=400)
        duration=visual[-1]['timestamp']-visual[0]['timestamp']
        if not 0<=duration<=3600000:
            return JsonResponse({'error':'Exportação disponível para sessões de até uma hora.'},status=400)
        try:token=replay_video.start(visual,owner,key)
        except RuntimeError as error:return JsonResponse({'error':str(error)},status=429)
        return JsonResponse({'job':token},status=202)
    if request.method!='GET':return HttpResponseNotAllowed(['GET','POST'])
    if request.GET.get('job'):
        rows_for(session)
        job=replay_video.get(request.GET['job'],owner)
        if not job:raise Http404('Exportação não encontrada. Gere novamente.')
        if request.GET.get('download')=='1' and job['state']=='ready':
            return FileResponse(job['path'].open('rb'),as_attachment=True,filename=f'pap-navegacao-{session}.webm',content_type='video/webm')
        return JsonResponse({'state':job['state']})
    rows_for(session)
    return render(request,'transit/usability_video.html',dict(admin.site.each_context(request),session=str(session),title='Exportar vídeo WebM'))
