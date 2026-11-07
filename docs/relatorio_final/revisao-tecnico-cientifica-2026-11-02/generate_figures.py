from pathlib import Path
import csv,json,hashlib,math,statistics
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import argparse
parser=argparse.ArgumentParser(description='Regera figuras somente a partir de insumos existentes.')
parser.add_argument('--report-root',type=Path,default=Path(__file__).resolve().parent.parent)
parser.add_argument('--benchmark-csv',type=Path,required=True)
parser.add_argument('--output-dir',type=Path)
args=parser.parse_args()
r=args.report_root
out=args.output_dir or r/'revisao-tecnico-cientifica-2026-11-02';out.mkdir(parents=True,exist_ok=True)
a=r/'auditoria-artesp-maua-2026-11-02'
src=args.benchmark_csv
with src.open() as f: rows=list(csv.DictReader(f))
paired=[x for x in rows if x['old_state']==x['new_state']=='first_route']
assert len(rows)==3264 and len(paired)==1637
old=np.array([float(x['old_first_seconds']) for x in paired]);new=np.array([float(x['new_first_seconds']) for x in paired]);delta=new-old
def stats(x):return {'n':len(x),'median':float(np.median(x)),'p95':float(sorted(x)[round(.95*(len(x)-1))]),'max':float(max(x))}
metrics={'all':{'before':stats(old),'after':stats(new)},'by_hour':{},'paired_differences':{'median':float(np.median(delta)),'improved':int(sum(delta<0)),'worse':int(sum(delta>0)),'equal':int(sum(delta==0))},'inputs':{}}
for hour in ['2','8','14']:
 q=[x for x in paired if x['hour']==hour];metrics['by_hour'][hour]={'before':stats([float(x['old_first_seconds']) for x in q]),'after':stats([float(x['new_first_seconds']) for x in q])}
plt.rcParams.update({'font.size':11,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42,'savefig.bbox':'tight'})
fig,axs=plt.subplots(2,1,figsize=(6.25,6.6),layout='constrained')
for x,label,color,style in [(old,'Antes','#184b78','-'),(new,'Depois','#b64719','--')]:
 axs[0].step(np.sort(x),np.arange(1,len(x)+1)/len(x),where='post',label=label,color=color,linestyle=style,lw=1.8)
axs[0].set(xlabel='Tempo até a primeira rota (s)',ylabel='Fração acumulada',title='(a) Distribuições dos mesmos 1.637 casos',xlim=(0,11),ylim=(0,1.01));axs[0].legend();axs[0].grid(alpha=.2)
# Every paired difference is retained, sorted only for readable display.
axs[1].plot(np.arange(1,len(delta)+1),np.sort(delta),color='#184b78',lw=1.5)
axs[1].axhline(0,color='black',lw=.8,ls='--');axs[1].set(xlabel='Caso pareado, ordenado pela diferença (1 a 1.637)',ylabel='Depois − antes (s)',title='(b) Diferenças individuais: abaixo de zero = menor tempo');axs[1].grid(alpha=.2)
fig.savefig(out/'benchmark-pareado.pdf');plt.close(fig)
summary=json.loads((a/'summary.json').read_text()); boundary=json.loads((a/'maua-ibge-2024.geojson').read_text())
with (a/'stops.csv').open() as f:stops=list(csv.DictReader(f))
assert len(stops)==len(set(x['stop_id'] for x in stops))==337
assert hashlib.sha256((a/'maua-ibge-2024.geojson').read_bytes()).hexdigest()==summary['boundary_geojson_sha256']
assert [summary['daily'][k]['trips'] for k in ['weekday','saturday','sunday']]==[705,427,359]
# Local equirectangular display in km; source coordinates unchanged.
lon0,lat0=-46.45,-23.67
def xy(lon,lat):return ((np.asarray(lon)-lon0)*111.32*math.cos(math.radians(lat0)),(np.asarray(lat)-lat0)*111.32)
fig,ax=plt.subplots(figsize=(6.25,6.0),layout='constrained');geom=boundary['geometry'];polys=geom['coordinates'] if geom['type']=='MultiPolygon' else [geom['coordinates']]
for rings in polys:
 for i,ring in enumerate(rings):
  pts=np.asarray(ring);x,y=xy(pts[:,0],pts[:,1]);ax.fill(x,y,color='#f2f2f2' if i==0 else 'white',zorder=0);ax.plot(x,y,color='#555555',lw=.8,zorder=1)
x,y=xy([float(s['stop_lon']) for s in stops],[float(s['stop_lat']) for s in stops]);ax.scatter(x,y,s=11,c='#135f95',alpha=.85,label='Paradas ARTESP (337)',zorder=2)
for i,s in enumerate(summary['rail_stations_already_present']):
 x,y=xy(s['stop_lon'],s['stop_lat']);ax.scatter(x,y,s=80,marker='D',c='#c43d22',edgecolors='white',linewidths=.9,zorder=3,label='Estações ferroviárias (3)' if i==0 else None)
 ax.annotate(s['stop_name'],(x,y),xytext=(12 if i!=1 else 20,13 if i!=1 else -15),textcoords='offset points',fontsize=11,fontweight='bold',bbox={'facecolor':'white','alpha':.9,'edgecolor':'none','pad':1},arrowprops={'arrowstyle':'-','color':'#444'},zorder=4)
ax.set_aspect('equal');ax.set(xlabel='Distância leste–oeste (km)',ylabel='Distância norte–sul (km)');ax.legend(loc='lower right',fontsize=10,framealpha=1)
ax.annotate('N',xy=(.94,.91),xytext=(.94,.80),xycoords='axes fraction',ha='center',arrowprops={'arrowstyle':'-|>','color':'black'})
ax.grid(alpha=.18);fig.savefig(out/'mapa-artesp-maua.pdf');plt.close(fig)
for p in [src,a/'stops.csv',a/'summary.json',a/'maua-ibge-2024.geojson']:
 metrics['inputs'][str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
(out/'metricas-recalculadas.json').write_text(json.dumps(metrics,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in metrics.items() if k!='inputs'},ensure_ascii=False,indent=2))
