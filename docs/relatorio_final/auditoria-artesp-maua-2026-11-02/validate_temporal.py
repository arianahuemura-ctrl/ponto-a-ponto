from pathlib import Path
from datetime import datetime,timedelta
import json,sqlite3
O=Path(__file__).parent;R=Path('/home/avale/Projetos/maua_bus_map');P=R/'artifacts/transport/artesp-20261102'
report=json.loads((O/'planning-queries.json').read_text());db=sqlite3.connect((P/'network.sqlite3').as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
cal={r['service_id']:dict(r) for r in db.execute('select * from calendar')};checked=0;journeys=0;trip_ids=set()
def sec(s):
 h,m,s=map(int,s.split(':'));return h*3600+m*60+s
for q in report['queries']:
 now=datetime.fromisoformat(q['query_at'])
 for j in q['result']['journeys']:
  journeys+=1;reached=now
  for index,leg in enumerate(j['legs']):
   walking=sum(w.get('seconds',w.get('duration_minutes',0)*60) for w in j['walks'] if w.get('before_leg')==index)
   departure=datetime.fromisoformat(leg['departure']);arrival=datetime.fromisoformat(leg['arrival'])
   assert departure>=reached+timedelta(seconds=walking)-timedelta(microseconds=10)
   assert arrival>=departure;reached=arrival
   if not leg['trip_id'].startswith('artesp:'):continue
   trip=db.execute('select * from trips where trip_id=?',(leg['trip_id'],)).fetchone()
   times=list(db.execute('select * from stop_times where trip_id=? order by stop_sequence',(leg['trip_id'],)))
   boarding,alighting=times[leg['boarding_index']],times[leg['alighting_index']]
   assert boarding['stop_id']==leg['origin']['id'] and alighting['stop_id']==leg['destination']['id']
   midnight=departure-timedelta(seconds=sec(boarding['departure_time']))
   assert midnight.hour==midnight.minute==midnight.second==0
   c=cal[trip['service_id']];d=midnight.strftime('%Y%m%d')
   assert c['start_date']<=d<=c['end_date'] and c[['monday','tuesday','wednesday','thursday','friday','saturday','sunday'][midnight.weekday()]]=='1'
   assert abs((arrival-midnight).total_seconds()-sec(alighting['arrival_time']))<1e-5
   checked+=1;trip_ids.add(leg['trip_id'])
  end=datetime.fromisoformat(j['arrival']);assert now<=end<=now+timedelta(hours=6)
out={'queries':len(report['queries']),'journeys_checked':journeys,'artesp_legs_checked_against_stop_times_and_calendar':checked,'distinct_artesp_trip_ids':len(trip_ids),'chronology_walks_and_six_hour_horizon_valid':True,'expired_calendar_control_empty':not report['queries'][-1]['result']['journeys'],'limitations':'Railway departures are frequency/engineering estimates, not exact observed train times. Validation does not imply exhaustive search or field operation.'}
(O/'temporal-validation.json').write_text(json.dumps(out,indent=2)+'\n');print(out)
