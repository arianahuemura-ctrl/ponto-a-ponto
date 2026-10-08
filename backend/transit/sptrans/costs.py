"""Perfis históricos versionados de circulação; GTFS continua sendo a alternativa programada.

Os perfis descrevem deslocamentos entre paradas GTFS adjacentes, sem as paradas programadas.
O tempo parado é somado uma única vez nas paradas intermediárias. Não se inferem observações.
"""
import csv
import math
from datetime import datetime, timedelta
from django.utils import timezone


def import_profiles(db, filename):
    rows=[]
    with open(filename,encoding='utf-8-sig',newline='') as stream:
        for r in csv.DictReader(stream):
            pid,index=int(r['pattern_id']),int(r['segment_index'])
            a,b=int(r['start_second']),int(r['end_second'])
            speed=float(r['speed_kmh']);samples=int(r['samples']);day=r['day_type']
            if day not in ('weekday','saturday','sunday','holiday') or not 0<=a<b<=86400:
                raise ValueError('Faixa/tipo de dia histórico inválido.')
            if not math.isfinite(speed) or not 0<speed<=130 or samples<1 or not r['source'].strip():
                raise ValueError('Perfil requer velocidade positiva, amostras e procedência.')
            if r.get('kind','running')!='running':
                raise ValueError('Importe velocidades de circulação sem parada; velocidade comercial requer decomposição antes da importação.')
            if not db.execute('SELECT 1 FROM connection_segments WHERE pattern_id=? AND segment_index=? AND distance_meters IS NOT NULL',
                              (pid,index)).fetchone():
                raise ValueError('Segmento histórico sem distância conhecida.')
            rows.append((pid,index,day,a,b,speed,r['source'],samples))
    # Valide o conjunto resultante, incluindo sobreposições com intervalos existentes.
    db.execute('SAVEPOINT profiles')
    try:
        db.executemany('INSERT OR REPLACE INTO historical_profiles VALUES (?,?,?,?,?,?,?,?)',rows)
        overlap=db.execute('''SELECT 1 FROM historical_profiles a JOIN historical_profiles b
            ON a.pattern_id=b.pattern_id AND a.segment_index=b.segment_index AND a.day_type=b.day_type
            AND a.start_second<b.start_second AND a.end_second>b.start_second LIMIT 1''').fetchone()
        if overlap: raise ValueError('Faixas históricas sobrepostas.')
        db.execute('RELEASE profiles')
    except Exception:
        db.execute('ROLLBACK TO profiles');db.execute('RELEASE profiles');raise
    return len(rows)


class Costs:
    def __init__(self, db, tz):
        self.db=db; self.tz=tz; self.profiles={};self.segments={};self.days={}

    def day_type(self, day):
        key=day.isoformat()
        if key not in self.days:
            row=self.db.execute('SELECT day_type FROM historical_days WHERE date=?',(key,)).fetchone()
            self.days[key]=row[0] if row else ('sunday' if day.weekday()==6 else 'saturday' if day.weekday()==5 else 'weekday')
        return self.days[key]

    def segment(self,pid,index,start):
        key=pid,index
        if key not in self.segments:
            row=self.db.execute('SELECT distance_meters FROM connection_segments WHERE pattern_id=? AND segment_index=?',key).fetchone()
            self.segments[key]=row[0] if row else None
        meters=self.segments[key]
        if meters is None or meters<=0:return None
        remaining=meters;clock=start
        # Todas as faixas atravessadas precisam de cobertura; caso contrário, use o custo GTFS integral do segmento.
        for _ in range(200):
            if remaining<=1e-7:return clock-start
            instant=datetime.fromtimestamp(clock,self.tz)
            day=self.day_type(instant.date());pkey=pid,index,day
            if pkey not in self.profiles:
                self.profiles[pkey]=list(self.db.execute('SELECT * FROM historical_profiles WHERE pattern_id=? AND segment_index=? AND day_type=? ORDER BY start_second',pkey))
            second=instant.hour*3600+instant.minute*60+instant.second+instant.microsecond/1e6
            band=next((r for r in self.profiles[pkey] if r['start_second']<=second<r['end_second']),None)
            if band is None:return None
            end=instant.replace(hour=0,minute=0,second=0,microsecond=0)+timedelta(seconds=band['end_second'])
            available=end.timestamp()-clock
            if available<=0:return None
            velocity=band['speed_kmh']/3.6
            elapsed=min(available,remaining/velocity)
            remaining-=elapsed*velocity;clock+=elapsed
        return None

    def ride(self,edge,times,departure):
        clock=departure;historical=0;fallback=0
        for i in range(edge['boarding_index'],edge['alighting_index']):
            duration=self.segment(edge['pattern_id'],i,clock)
            if duration is None:
                duration=times[i+1][1]-times[i][2];fallback+=1
            else:historical+=1
            clock+=duration
            if i+1<edge['alighting_index']:
                clock+=times[i+1][2]-times[i+1][1]
        return clock-departure, {'historical_segments':historical,'scheduled_segments':fallback}
