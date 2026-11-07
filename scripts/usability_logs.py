#!/usr/bin/env python3
from telemetry_storage import read_rows
"""Lista sessões ou exporta eventos JSONL, apenas localmente."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--session',help='UUID completo da sessão a exportar')
args=parser.parse_args()
path=Path.home()/'.local/state/pap/usability/events.sqlite3'
if not path.exists():raise SystemExit('Nenhum evento recebido ainda.')
with sqlite3.connect(path.as_uri()+'?mode=ro',uri=True) as db:
    if args.session:
        for seq,received,kind,data in read_rows(db,args.session):
            print(json.dumps({'session':args.session,'seq':seq,'received_utc':datetime.fromtimestamp(received,timezone.utc).isoformat(),'type':kind,'data':json.loads(data)},ensure_ascii=False))
    else:
        for session,count,start,end in db.execute('SELECT session,COUNT(*),MIN(received),MAX(received) FROM events GROUP BY session ORDER BY MAX(received) DESC'):
            print(session,count,'eventos',datetime.fromtimestamp(start,timezone.utc).isoformat(),datetime.fromtimestamp(end,timezone.utc).isoformat())
