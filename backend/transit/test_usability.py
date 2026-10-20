import json
import sqlite3
import tempfile
from pathlib import Path
from django.test import SimpleTestCase, Client, override_settings

class UsabilityTests(SimpleTestCase):
    def test_sessions_validation_csrf_and_storage(self):
        with tempfile.TemporaryDirectory() as folder, override_settings(PAP_USABILITY_DB=Path(folder)/'events.sqlite3'):
            client=Client(enforce_csrf_checks=True)
            first=client.get('/api/usability/').json()
            second=client.get('/api/usability/').json()
            self.assertNotEqual(first['session'],second['session'])
            self.assertEqual(client.get('/api/usability/',HTTP_X_PAP_SESSION=first['token']).json()['session'],first['session'])
            payload={'token':first['token'],'events':[{'type':'action','seq':1,'data':{'target':'lamp'}}]}
            self.assertEqual(client.post('/api/usability/',data=json.dumps(payload),content_type='application/json').status_code,403)
            def send(value):return client.post('/api/usability/',data=json.dumps(value),content_type='application/json',HTTP_X_CSRFTOKEN=first['csrf'])
            self.assertEqual(send(payload).status_code,200)
            self.assertEqual(send(payload).status_code,200)
            payload['events'][0]['data']['latitude']=-23.55
            self.assertEqual(send(payload).status_code,400)
            payload['token']='invalid'
            self.assertEqual(send(payload).status_code,400)
            with sqlite3.connect(Path(folder)/'events.sqlite3') as db:
                rows=db.execute('SELECT session,type,data FROM events').fetchall()
            self.assertEqual(rows,[(first['session'],'action','{"target":"lamp"}')])

    def test_rate_limit(self):
        with tempfile.TemporaryDirectory() as folder, override_settings(PAP_USABILITY_DB=Path(folder)/'events.sqlite3'):
            info=self.client.get('/api/usability/').json()
            for batch in range(150):
                events=[{'type':'action','seq':batch*20+i,'data':{'target':'lamp'}} for i in range(20)]
                self.assertEqual(self.client.post('/api/usability/',data=json.dumps({'token':info['token'],'events':events}),content_type='application/json').status_code,200)
            self.assertEqual(self.client.post('/api/usability/',data=json.dumps({'token':info['token'],'events':events}),content_type='application/json').status_code,429)

    def test_trace_contract(self):
        from transit.usability import validate
        payload=json.dumps({'kind':'input','details':{'query':'Rebouças','lat':-23.55012345}})
        result=validate([{'type':'trace','seq':1,'data':{'payload':payload}}])
        self.assertEqual(json.loads(result[0][2])['payload'],payload)
        with self.assertRaises(ValueError):validate([{'type':'trace','seq':1,'data':{'payload':'x'*12001}}])

    def test_feedback_storage_validation_and_deduplication(self):
        with tempfile.TemporaryDirectory() as folder,override_settings(PAP_USABILITY_DB=Path(folder)/'events.sqlite3'):
            info=self.client.get('/api/usability/').json()
            feedback={'category':'problema','message':'O mapa travou','at':'2026-10-19T20:00:00Z','elapsed':1234}
            payload={'token':info['token'],'events':[{'type':'feedback','seq':55,'data':{'payload':json.dumps(feedback)}}]}
            def send():return self.client.post('/api/usability/',data=json.dumps(payload),content_type='application/json')
            self.assertEqual(send().status_code,200);self.assertEqual(send().status_code,200)
            with sqlite3.connect(Path(folder)/'events.sqlite3') as db:
                rows=db.execute('SELECT session,type,data FROM events').fetchall()
            self.assertEqual(len(rows),1);self.assertEqual(rows[0][0],info['session']);self.assertEqual(json.loads(json.loads(rows[0][2])['payload']),feedback)
            feedback['message']=' '
            payload['events'][0]['data']['payload']=json.dumps(feedback)
            self.assertEqual(send().status_code,400)

    def test_invalid_trace_and_global_capacity_preserve_rows(self):
        from transit.usability import validate
        from scripts.export_replay import reconstruct
        for payload in ['{}','[]','{"kind":"visual","details":{}}']:
            with self.assertRaises(ValueError):validate([{'type':'trace','seq':1,'data':{'payload':payload}}])
            events,invalid=reconstruct([(1,0,'trace',json.dumps({'payload':payload}))])
            self.assertEqual(events,[]);self.assertTrue(invalid)
        with tempfile.TemporaryDirectory() as folder,override_settings(PAP_USABILITY_DB=Path(folder)/'events.sqlite3',PAP_TELEMETRY_MAX_EVENTS=1):
            first=self.client.get('/api/usability/').json()
            second=self.client.get('/api/usability/').json()
            def send(token):return self.client.post('/api/usability/',data=json.dumps({'token':token,'events':[{'type':'action','seq':1,'data':{'target':'lamp'}}]}),content_type='application/json')
            self.assertEqual(send(first['token']).status_code,200)
            self.assertEqual(send(second['token']).status_code,503)
            with sqlite3.connect(Path(folder)/'events.sqlite3') as db:self.assertEqual(db.execute('SELECT session FROM events').fetchall(),[(first['session'],)])

    def test_global_limits_apply_across_sessions(self):
        for limits in [{'PAP_TELEMETRY_EVENTS_PER_MINUTE':1},{'PAP_TELEMETRY_BYTES_PER_MINUTE':20},{'PAP_TELEMETRY_MAX_BYTES':20}]:
            with tempfile.TemporaryDirectory() as folder,override_settings(PAP_USABILITY_DB=Path(folder)/'events.sqlite3',**limits):
                def send():
                    token=self.client.get('/api/usability/').json()['token']
                    return self.client.post('/api/usability/',data=json.dumps({'token':token,'events':[{'type':'action','seq':1,'data':{'target':'lamp'}}]}),content_type='application/json')
                self.assertEqual(send().status_code,200)
                self.assertEqual(send().status_code,503 if 'PAP_TELEMETRY_MAX_BYTES' in limits else 429)
