"""32 independent read-only census processes; no HTTP requests or data mutation."""
import concurrent.futures,json,os,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];os.chdir(ROOT)
OUT=ROOT/'artifacts/benchmarks/coverage-audit-20261101';OUT.mkdir(exist_ok=True)
N=22274;WORKERS=32
started=time.monotonic()
def shard(i):
 a=N*i//WORKERS;b=N*(i+1)//WORKERS;target=OUT/f'census-{i:02d}.jsonl'
 if target.exists():
  rows=[json.loads(l) for l in target.read_text().splitlines()]
  if [r['origin'] for r in rows]==list(range(a,b)):return i
 subprocess.run([str(ROOT/'.cache/staged/coverage-census'),str(ROOT/'sptrans.staged.sqlite3'),str(a),str(b),str(N),str(target)],check=True)
 return i
with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
 for result in pool.map(shard,range(WORKERS)):print('shard complete',result,flush=True)
rows=[json.loads(l) for p in OUT.glob('census-*.jsonl') for l in p.read_text().splitlines()]
assert sorted(r['origin'] for r in rows)==list(range(N))
hist=[sum(r['histogram'][i] for r in rows) for i in range(6)]
assert sum(hist)==N*(N-1)
report={'stops':N,'directed_pairs':sum(hist),'histogram_routes_per_pair':hist,'covered_pairs':sum(hist[1:]),'missing_pairs':hist[0],'routes':sum(i*c for i,c in enumerate(hist)),'workers':WORKERS,'wall_seconds':time.monotonic()-started,'rows_scanned':sum(r['rows_scanned'] for r in rows),'scope':'Exhaustive counts; batch throughput is NOT time to first journey'}
(OUT/'census-summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
