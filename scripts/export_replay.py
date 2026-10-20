#!/usr/bin/env python3
"""Exportação local e comparação de camadas da mesma sessão."""
import argparse,collections,gzip,html,json,os,sqlite3,shutil
from pathlib import Path

def reconstruct(rows):
    events=[];chunks={};missing=[]
    def check(e):
        if not isinstance(e,dict) or not isinstance(e.get('kind'),str) or not isinstance(e.get('details'),dict):raise ValueError()
        if e['kind']=='visual':
            v=e['details']
            if type(v.get('timestamp')) not in (int,float) or not __import__('math').isfinite(v['timestamp']) or not isinstance(v.get('data'),dict) or type(v.get('type')) is not int:raise ValueError()
        return e
    for seq,received,kind,data in rows:
        try:
            item=json.loads(data)
            if not isinstance(item,dict):raise ValueError()
            if kind!='trace':events.append(dict(seq=seq,kind=kind,details=item,received=received));continue
            e=json.loads(item['payload'])
            if e['kind']=='chunk':
                if not isinstance(e['id'],str) or type(e['total']) is not int or not 1<=e['total']<=2048 or type(e['index']) is not int or not 0<=e['index']<e['total'] or not isinstance(e['text'],str) or len(e['text'])>8000:raise ValueError()
                chunks.setdefault(e['id'],[]).append((seq,e));continue
            events.append({**check(e),'seq':seq})
        except (ValueError,TypeError,KeyError,RecursionError):missing.append('invalid:'+str(seq))
    for key,parts in chunks.items():
        try:
            parts.sort(key=lambda x:x[1]['index'])
            total=parts[0][1]['total']
            if len(parts)!=total or any(p['total']!=total for _,p in parts) or [x[1]['index'] for x in parts]!=list(range(total)):raise ValueError()
            e=check(json.loads(''.join(x[1]['text'] for x in parts)))
            events.append({**e,'seq':min(x[0] for x in parts)})
        except (ValueError,TypeError,KeyError,RecursionError):missing.append(key)
    return sorted(events,key=lambda e:e['seq']),missing

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--session',required=True);parser.add_argument('--output',required=True);args=parser.parse_args()
    os.umask(0o077);out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    dbpath=Path.home()/'.local/state/pap/usability/events.sqlite3'
    with sqlite3.connect(dbpath.as_uri()+'?mode=ro',uri=True) as db:rows=db.execute('SELECT seq,received,type,data FROM events WHERE session=? ORDER BY seq',(args.session,)).fetchall()
    if not rows:raise SystemExit('Sessão não encontrada')
    events,incomplete=reconstruct(rows)
    basic=[e for e in events if e['kind'] in {'session_start','state','action','api','error','dimmer'}]
    detailed=[e for e in events if e['kind'] not in {'visual','visual_config'}]
    visual=[e['details'] for e in events if e['kind']=='visual']
    visual_dom=[e for e in visual if not (e.get('type')==3 and e.get('data',{}).get('source')==9)]
    groups={'basico':basic,'diagnostico':detailed,'visual_sem_canvas':visual_dom,'visual':visual,'completo':events};sizes={}
    for name,data in groups.items():
        content=json.dumps(data,ensure_ascii=False,separators=(',',':')).encode();compressed=gzip.compress(content,mtime=0)
        (out/f'{name}.json').write_bytes(content);(out/f'{name}.json.gz').write_bytes(compressed)
        sizes[name]={'eventos':len(data),'bytes':len(content),'gzip_bytes':len(compressed)}
    sequences={r[0] for r in rows};gaps=sorted(set(range(rows[0][0],rows[-1][0]+1))-sequences)
    report=dict(session=args.session,sizes=sizes,missing_sequences=gaps,incomplete_chunks=incomplete,stored_data_bytes=sum(len(r[3].encode()) for r in rows),duration_received_seconds=rows[-1][1]-rows[0][1])
    report['player_asset_bytes']=sum((Path(__file__).resolve().parents[1]/'frontend/node_modules/rrweb-player/dist'/name).stat().st_size for name in ['rrweb-player.umd.cjs','style.css'])
    (out/'comparacao.json').write_text(json.dumps(report,indent=2))
    table=''.join(f'<tr><td>{html.escape(k)}</td><td>{v["eventos"]}</td><td>{v["bytes"]:,}</td><td>{v["gzip_bytes"]:,}</td></tr>' for k,v in sizes.items())
    header=f'<h1>Reprodução e comparação PaP</h1><p>Sessão {html.escape(args.session)}</p><table><tr><th>Camada</th><th>Eventos</th><th>Bytes JSON</th><th>Bytes gzip</th></tr>{table}</table><p>Básico está incluído em diagnóstico; visual sem canvas está incluído em visual; completo inclui diagnóstico e visual. Não some as linhas. Gzip é exportação, não compressão do banco. Bibliotecas do player são cópias adicionais, medidas em comparacao.json.</p><p>Lacunas: {len(gaps)}; grupos incompletos: {len(incomplete)}. Bytes de dados no SQLite (sem índices/páginas): {report["stored_data_bytes"]:,}.</p>'
    assets=Path(__file__).resolve().parents[1]/'frontend/node_modules/rrweb-player/dist'
    for source,dest in [('rrweb-player.umd.cjs','player.js'),('style.css','player.css')]:shutil.copyfile(assets/source,out/dest)
    shutil.copyfile(Path(__file__).resolve().parents[1]/'backend/transit/static/transit/replay-theme.js',out/'replay-theme.js')
    payload=json.dumps(visual,ensure_ascii=False).replace('<','\\u003c')
    page='''<!doctype html><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src data: blob: https: http:; font-src data: https:; frame-src 'self' blob:; connect-src 'none'"><title>Reprodução PaP</title><link rel="stylesheet" href="player.css"><style>body{font:16px system-ui;margin:24px;background:#112136;color:white}td,th{padding:10px;text-align:left}#player{margin-top:20px}</style>'''+header+'''<p>Player local: sem consultas à API ou ações reais. Imagens externas podem exigir rede. A gravação de canvas usa 5 quadros/s, não vídeo integral.</p><div id="player"></div><script src="player.js"></script><script src="replay-theme.js"></script><script type="application/json" id="events">'''+payload+'''</script><script>const events=JSON.parse(document.getElementById('events').textContent);if(location.protocol==='file:'){document.getElementById('player').textContent='Abra este replay por HTTP local. Na pasta exportada, execute: python3 -m http.server 8766 --bind 127.0.0.1. Depois acesse http://127.0.0.1:8766/replay.html';}else if(events.length>=2){const player=new (rrwebPlayer.default||rrwebPlayer)({target:document.getElementById('player'),props:{events,autoPlay:false,width:Math.min(innerWidth-60,1100),height:650,UNSAFE_replayCanvas:true,speedOption:[0.5,1,2,4]}});papReplayTheme(player,events);let pending;const resize=()=>{cancelAnimationFrame(pending);pending=requestAnimationFrame(()=>{player.$set({width:Math.max(1,Math.min(document.documentElement.clientWidth-48,1100)),height:Math.max(200,innerHeight-100)});player.triggerResize();});};window.addEventListener('resize',resize);resize();}else{document.getElementById('player').textContent='Esta sessão não contém captura visual suficiente.'}</script>'''
    (out/'replay.html').write_text(page)
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
