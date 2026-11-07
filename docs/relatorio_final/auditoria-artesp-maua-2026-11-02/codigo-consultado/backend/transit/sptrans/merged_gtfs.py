"""Publish a separate SPTrans + ARTESP catalogue, preserving source identifiers."""
import csv
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import zipfile
from django.utils import timezone
from . import store

IDENTIFIERS = {'stop_id', 'route_id', 'trip_id', 'service_id', 'shape_id', 'agency_id', 'fare_id'}


def merge(base, archive, target, progress=print):
    base, archive, target = map(Path, (base, archive, target))
    if target.exists() or target.resolve() == base.resolve():
        raise ValueError('A saída deve ser nova e diferente da base original.')
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_suffix('.importing.sqlite3')
    if temp.exists():
        raise ValueError('Já existe uma importação temporária; examine-a antes de repetir.')
    report = {'imported_at': timezone.now().isoformat(), 'namespace': 'artesp:',
              'source_base': str(base.resolve()), 'archive': str(archive.resolve()),
              'archive_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(), 'added': {}}
    with sqlite3.connect(base.resolve().as_uri()+'?mode=ro', uri=True) as src, sqlite3.connect(temp) as db, zipfile.ZipFile(archive) as z:
        src.backup(db)
        db.execute('PRAGMA temp_store=FILE')
        for table, cols in store.TABLES.items():
            filename = table+'.txt'
            if filename not in z.namelist():
                if table not in ('frequencies', 'calendar_dates'):
                    raise ValueError('Tabela obrigatória ausente: '+filename)
                report['added'][table] = 0
                continue
            if table in ('stops', 'routes', 'trips', 'calendar', 'shapes'):
                key = {'stops':'stop_id', 'routes':'route_id', 'trips':'trip_id', 'calendar':'service_id', 'shapes':'shape_id'}[table]
                if db.execute(f'SELECT 1 FROM {table} WHERE {key} LIKE ? LIMIT 1', ('artesp:%',)).fetchone():
                    raise ValueError('Namespace ARTESP já utilizado pela base.')
            count = 0
            def converted():
                nonlocal count
                for row in csv.DictReader(io.TextIOWrapper(z.open(filename), encoding='utf-8-sig')):
                    if table == 'stop_times':
                        a, d = store.seconds(row['arrival_time']), store.seconds(row['departure_time'])
                        if a < 0 or d < a:
                            raise ValueError('Horário GTFS inválido: '+str(row))
                    count += 1
                    yield ['artesp:'+row[c] if c in IDENTIFIERS and row.get(c) else row.get(c, '') for c in cols]
            db.executemany(f'INSERT INTO {table} VALUES ('+','.join('?' for _ in cols)+')', converted())
            db.commit()
            report['added'][table] = count
            progress(f'{table}: +{count}', flush=True)
        # Preserve ancillary source tables even though routing does not consume fares.
        for table in ('agency', 'feed_info', 'fare_attributes', 'fare_rules'):
            reader = csv.DictReader(io.TextIOWrapper(z.open(table+'.txt'), encoding='utf-8-sig'))
            cols = reader.fieldnames
            db.execute(f'CREATE TABLE source_artesp_{table} ('+','.join('"'+c+'" TEXT' for c in cols)+')')
            db.executemany(f'INSERT INTO source_artesp_{table} VALUES ('+','.join('?' for _ in cols)+')',
                           ([row[c] for c in cols] for row in reader))
        for child, parent, key in [('stop_times','stops','stop_id'), ('stop_times','trips','trip_id'), ('trips','routes','route_id')]:
            missing = db.execute(f'SELECT count(*) FROM {child} c WHERE NOT EXISTS (SELECT 1 FROM {parent} p WHERE p.{key}=c.{key})').fetchone()[0]
            if missing:
                raise ValueError(f'{missing} referências sem destino em {child}.{key}')
        for table, key in [('stops','stop_id'), ('trips','trip_id'), ('routes','route_id')]:
            if db.execute(f'SELECT 1 FROM {table} GROUP BY {key} HAVING count(*)>1 LIMIT 1').fetchone():
                raise ValueError('Identificadores duplicados em '+table)
        report['trips_without_stop_times'] = db.execute('SELECT count(*) FROM trips t WHERE NOT EXISTS (SELECT 1 FROM stop_times s WHERE s.trip_id=t.trip_id)').fetchone()[0]
        report['counts'] = {t: db.execute(f'SELECT count(*) FROM {t}').fetchone()[0] for t in store.TABLES}
        report['limitations'] = ['ARTESP intermediate times are interpolated', 'ARTESP calendar lacks holiday exceptions', 'No realtime ARTESP feed imported']
        db.execute('UPDATE metadata SET value=?', (json.dumps(report),))
        db.execute('ANALYZE')
        db.commit()
        if db.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
            raise ValueError('Falha de integridade da importação.')
    temp.replace(target)
    return report
