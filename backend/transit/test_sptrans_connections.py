import csv
import json
import math
import sqlite3
from datetime import timedelta
from unittest.mock import patch
from django.test import SimpleTestCase, override_settings
from transit import test_sptrans_graph as fixtures
from transit.sptrans import direct, city_connections, materialized_connections, materialized_adapter, catalog, costs, connection_planner, graph, connection_adapter, store, alternatives


class ConnectionsTests(SimpleTestCase):
    def setUp(self):
        fixtures.GraphTests.setUp(self)
        catalog.install(self.index)
        with self.db() as db:catalog.build_pair(db,'A','D')

    db=fixtures.GraphTests.db

    def run_query(self,**kw):
        return connection_planner.query('A','D',now=fixtures.NOW,path=self.index,operational=False,**kw)

    def test_catalog_has_each_category_and_structural_identities(self):
        with self.db() as db:
            rows,meta=catalog.candidates(db,'A','D')
            self.assertTrue(meta['complete'])
            self.assertEqual({r['boardings'] for r in rows},{1,2,3})
            for row in rows:
                self.assertAlmostEqual(row['distance_meters'],row['bus_meters']+row['walk_meters'])
                described=catalog.describe(db,row)
                self.assertTrue(all(l['servicos'][0]['destino_letreiro']=='Destino' for l in described['trechos'] if l['modo']=='onibus'))

    def test_top_k_by_distance_not_insertion_order(self):
        with self.db() as db:
            edge=dict(db.execute("SELECT * FROM ride_edge WHERE origin='A' AND destination='D'").fetchone())
            for i in range(30):
                # Padrões sintéticos distintos, inseridos do mais longo para o mais curto.
                db.execute('INSERT INTO ride_edge(origin,destination,pattern_id,boarding_index,alighting_index,distance_meters,min_ride_seconds) VALUES (?,?,?,?,?,?,?)',
                    ('A','D',900+i,0,1,1000-i,60))
            catalog.build_pair(db,'A','D',force=True)
            rows=list(db.execute('SELECT distance_meters FROM connections WHERE boardings=1 ORDER BY rank'))
            self.assertEqual(len(rows),16)
            self.assertEqual([r[0] for r in rows],list(range(971,987)))

    def test_offline_no_external_calls_and_five_minute_preliminary_only(self):
        with patch.object(connection_planner.realtime,'add_predictions',side_effect=AssertionError('network')):
            result=self.run_query()
        self.assertEqual(result['journeys'][0]['duration_seconds'],2400)
        j=result['journeys'][0]
        self.assertEqual(j['transfer_buffer_seconds'],240)
        self.assertEqual(j['wait_seconds'],360)
        self.assertEqual(j['duration_seconds'],sum(j[k] for k in ('access_seconds','egress_seconds','ride_seconds','wait_seconds','transfer_walk_seconds','transfer_buffer_seconds')))
        with self.db() as db:
            engine=connection_planner.Evaluator(db,fixtures.NOW,False)
            candidate=next(r for r in catalog.candidates(db,'A','D')[0] if r['boardings']==3)
            self.assertEqual(engine.preliminary(candidate),2400) # Trajetos de 30 min + 2*5 min.

    def test_access_misses_bus(self):
        self.assertEqual(self.run_query(access_seconds=360)['journeys'],[])

    def test_missed_operational_vehicle_not_boarded(self):
        def provider(row,stop):
            row['arrivals']=[{'time':'08:03','vehicle':'123','observed_at':fixtures.NOW.isoformat()}]
        r=connection_planner.query('A','D',now=fixtures.NOW,path=self.index,provider=provider,access_seconds=360)
        self.assertEqual(r['journeys'],[])

    def test_operational_delay_invalidates_transfer(self):
        def provider(row,stop):
            if row['code']=='R1':row['arrivals']=[{'time':'08:10','vehicle':'123','observed_at':fixtures.NOW.isoformat()}]
        r=connection_planner.query('A','D',now=fixtures.NOW,path=self.index,provider=provider)
        self.assertEqual([j['transfers'] for j in r['journeys']],[0])

    def test_prediction_rescues_delayed_scheduled_departure(self):
        def provider(row,stop):
            if row['code']=='DIRECT':row['arrivals']=[{'time':'08:10','vehicle':'123','observed_at':fixtures.NOW.isoformat()}]
        r=connection_planner.query('A','D',now=fixtures.NOW,path=self.index,provider=provider,access_seconds=360)
        self.assertEqual(len(r['journeys']),1)
        self.assertEqual(r['journeys'][0]['duration_seconds'],4200)
        self.assertEqual(r['journeys'][0]['legs'][0]['timing_source'],'olho_vivo')

    def test_unavailable_api_retains_programme(self):
        def provider(row,stop):raise connection_planner.APIError('offline')
        r=connection_planner.query('A','D',now=fixtures.NOW,path=self.index,provider=provider)
        self.assertEqual(r['journeys'][0]['duration_seconds'],2400)
        self.assertEqual(r['api_lookups'],1)
        self.assertTrue(r['warnings'])

    def test_stale_prediction_ignored(self):
        def provider(row,stop):
            row['arrivals']=[{'time':'08:10','vehicle':'123','observed_at':(fixtures.NOW-timedelta(hours=1)).isoformat()}]
        r=connection_planner.query('A','D',now=fixtures.NOW,path=self.index,provider=provider)
        self.assertTrue(all(l['timing_source']=='programme' for j in r['journeys'] for l in j['legs']))

    def test_forecast_deduplicated_and_mapping_persisted(self):
        calls=[]
        def provider(row,stop):
            calls.append((row['code'],stop['id']));row.update(api_line=42,api_stop=11)
        r=connection_planner.query('A','D',now=fixtures.NOW,path=self.index,provider=provider)
        self.assertEqual(len(calls),len(set(calls)))
        with self.db() as db:
            self.assertGreater(db.execute('SELECT COUNT(*) FROM connection_operational_mappings').fetchone()[0],0)

    def test_walk_revision_rejects_catalogue_then_rebuilds(self):
        with self.db() as db:
            graph.put_walk(db,'B','E',{'available':False})
            with self.assertRaisesRegex(ValueError,'desatualizado'):catalog.candidates(db,'A','D')
            catalog.build_pair(db,'A','D')
            self.assertTrue(catalog.candidates(db,'A','D')[1]['complete'])

    def test_verified_walk_time_and_distance_persist(self):
        with self.db() as db:
            a=db.execute("SELECT lat,lon FROM graph_stop WHERE id='B'").fetchone()
            b=db.execute("SELECT lat,lon FROM graph_stop WHERE id='E'").fetchone()
            graph.put_walk(db,'B','E',{'available':True,'distance_meters':75,'geometry':[list(a),list(b)]})
            catalog.build_pair(db,'A','C')
            rows,_=catalog.candidates(db,'A','C')
            walk=next(r for r in rows if r['walk_meters'])
            self.assertEqual(walk['walk_seconds'],60)
            self.assertEqual(catalog.describe(db,walk)['tempo_caminhada_s'],60)

    def test_no_static_rebuild_during_query(self):
        with patch.object(graph,'build',side_effect=AssertionError()),patch.object(catalog,'build_pair',side_effect=AssertionError()):
            self.run_query()

    def test_progressive_final_status_and_stable_ids(self):
        chunks=list(connection_planner.progressive('A','D',now=fixtures.NOW,path=self.index,operational=False))
        self.assertFalse(chunks[0]['complete']);self.assertTrue(chunks[-1]['complete'])
        self.assertTrue(all(len(c['journeys'])<=5 for c in chunks))
        self.assertFalse(chunks[-1]['optimal_globally'])
        self.assertEqual([j['id'] for j in chunks[-1]['journeys']],[j['id'] for j in self.run_query()['journeys']])

    def profile_file(self,rows):
        path=self.root/'profiles.csv'
        with path.open('w') as f:
            writer=csv.writer(f);writer.writerow(['pattern_id','segment_index','day_type','start_second','end_second','speed_kmh','source','samples'])
            writer.writerows(rows)
        return path

    def test_history_crosses_time_band_and_day_boundary(self):
        with self.db() as db:
            pid=db.execute("SELECT id FROM pattern WHERE code='R1'").fetchone()[0]
            db.execute('UPDATE connection_segments SET distance_meters=1500 WHERE pattern_id=?',(pid,))
            path=self.profile_file([(pid,0,'weekday',0,28860,36,'fixture',10),(pid,0,'weekday',28860,86400,18,'fixture',10)])
            self.assertEqual(costs.import_profiles(db,path),2)
            model=costs.Costs(db,fixtures.NOW.tzinfo)
            self.assertEqual(model.segment(pid,0,fixtures.NOW.timestamp()),240) # 600m/36 + 900m/18
            # Meia-noite: últimos 30 s a 18 km/h, 1350 m restantes a 36 km/h.
            start=fixtures.NOW.replace(hour=23,minute=59,second=30)
            self.assertEqual(model.segment(pid,0,start.timestamp()),165)

    def test_history_missing_coverage_falls_back_not_fabricated(self):
        with self.db() as db:
            engine=connection_planner.Evaluator(db,fixtures.NOW,False)
            edge=engine.edge(db.execute("SELECT id FROM ride_edge WHERE origin='A' AND destination='B'").fetchone()[0])
            tt=engine.schedule(edge)[0][1]
            duration,source=engine.costs.ride(edge,tt,fixtures.NOW.timestamp())
            self.assertEqual(duration,600);self.assertEqual(source['historical_segments'],0)

    def test_history_overlap_rejected_atomically(self):
        with self.db() as db:
            pid=db.execute("SELECT id FROM pattern WHERE code='R1'").fetchone()[0]
            f=self.profile_file([(pid,0,'weekday',0,100,20,'fixture',1),(pid,0,'weekday',50,200,20,'fixture',1)])
            with self.assertRaisesRegex(ValueError,'sobrepostas'):costs.import_profiles(db,f)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM historical_profiles').fetchone()[0],0)

    def test_pruning_preserves_five_not_only_winner(self):
        # Injete 12 candidatos e um avaliador simples para isolar o contrato de seleção.
        with self.db() as db:
            base=dict(db.execute('SELECT * FROM connections LIMIT 1').fetchone())
            db.execute('DELETE FROM connections')
            for i in range(12):
                db.execute('INSERT INTO connections VALUES (?,?,?,?,?,?,?,?,?,?)',
                    (str(i),'A','D',1,i+1,100+i,100+i,0,0,base['edge_ids']))
        ceilings=[]
        def evaluate(engine,candidate,access,egress,ceiling):
            i=int(candidate['id']);ceilings.append(ceiling)
            # O décimo primeiro candidato vence: os dez iniciais não são um limite rígido.
            duration=50 if i==10 else 100+i
            if duration>ceiling:return None,'pruned'
            return {'id':candidate['id'],'duration_seconds':duration,'transfers':0,'walking_seconds':0},'evaluated'
        with patch.object(connection_planner.Evaluator,'preliminary',lambda self,c,a,e:int(c['id'])),patch.object(connection_planner.Evaluator,'evaluate',evaluate):
            r=self.run_query()
        self.assertEqual([j['id'] for j in r['journeys']],['10','0','1','2','3'])
        self.assertTrue(all(math.isinf(x) for x in ceilings[:5]));self.assertEqual(ceilings[5],104)

    def test_adapter_preserves_app_contract(self):
        result=self.run_query()['journeys'][0]
        with store.connection() as db:
            row=connection_adapter.journey(db,result)
        self.assertEqual(row['duration_minutes'],40)
        self.assertEqual(row['legs'][0]['origin']['id'],'A')
        self.assertTrue(row['legs'][0]['geometry'])

    def test_cancelled_build_never_claims_top_k_complete(self):
        with self.db() as db:
            # Trabalho suficiente para acionar o callback de progresso do SQLite.
            db.executemany('INSERT INTO ride_edge(origin,destination,pattern_id,boarding_index,alighting_index,distance_meters,min_ride_seconds) VALUES (?,?,?,?,?,?,?)',
                [('A','B',1000+i,0,1,100+i,60) for i in range(150)])
            # Force cada callback de progresso do SQLite a ultrapassar o prazo.
            ticks=iter(range(1000000))
            with patch.object(catalog.time,'monotonic',side_effect=lambda:next(ticks)):
                r=catalog.build_pair(db,'A','D',seconds=1e-12,force=True)
            self.assertFalse(r['complete'])
            self.assertTrue(any(not c['complete'] for c in r['categories'].values()))

    def prepare_physical(self):
        dp=self.root/'direct.sqlite3';cp=self.root/'components.sqlite3'
        direct.build(source=self.index,target=dp)
        city_connections.build(source=dp,graph_source=self.index,target=cp)
        materialized_connections.materialize([('A','D')],source=cp,min_free_bytes=0)

    def test_app_opt_in_uses_catalogue_and_preserves_stream(self):
        self.prepare_physical()
        with override_settings(SPTRANS_PLANNER='connections'),patch.object(graph,'graph_path',return_value=self.index),patch.object(connection_planner.realtime,'add_predictions',lambda row,stop:None):
            with store.connection() as db:
                origin=store.get_stop(db,'A');destination=store.get_stop(db,'D')
                chunks=list(alternatives.progressive(db,origin,destination,now=fixtures.NOW))
        self.assertEqual(chunks[-1]['planner'],'connections')
        self.assertTrue(chunks[-1]['complete'])
        self.assertEqual(chunks[-1]['journeys'][0]['duration_minutes'],40)

    def test_mandatory_walk_is_safe_bound(self):
        with self.db() as db:
            engine=connection_planner.Evaluator(db,fixtures.NOW,False)
            candidate=catalog.candidates(db,'A','D')[0][0]
            with patch.object(engine,'choices',side_effect=AssertionError('unnecessary refinement')):
                row,state=engine.evaluate(candidate,access=301,ceiling=300)
            self.assertIsNone(row);self.assertEqual(state,'pruned')

    def test_history_ranking_is_not_used_as_a_pruning_bound(self):
        with patch.object(connection_planner.Evaluator,'preliminary',return_value=999999):
            result=self.run_query()
        self.assertEqual(result['journeys'][0]['duration_seconds'],2400)

    def test_day_exception_removes_all_services(self):
        with self.db() as db:
            db.execute("INSERT INTO calendar_dates VALUES ('daily','20261007','2')")
        self.assertEqual(self.run_query()['journeys'],[])

    def test_scheduled_dwell_added_once_with_running_profiles(self):
        with self.db() as db:
            engine=connection_planner.Evaluator(db,fixtures.NOW,False)
            with patch.object(engine.costs,'segment',return_value=100):
                duration,_=engine.costs.ride({'pattern_id':1,'boarding_index':0,'alighting_index':2},
                    [['A',0,0],['B',100,130],['C',230,260]],fixtures.NOW.timestamp())
        self.assertEqual(duration,230) # Dois deslocamentos de 100 s, apenas a parada intermediária de 30 s.

    def test_same_origin_destination_is_empty(self):
        with self.db() as db:
            r=catalog.build_pair(db,'A','A');self.assertEqual(r['candidate_count'],0)

    def test_naive_clock_and_negative_walk_rejected(self):
        with self.assertRaises(ValueError):self.run_query(access_seconds=-1)
        with self.assertRaises(ValueError):connection_planner.query('A','D',now=fixtures.NOW.replace(tzinfo=None),path=self.index)

    def test_zero_projected_distance_does_not_erase_scheduled_travel(self):
        with self.db() as db:
            db.execute('UPDATE connection_segments SET distance_meters=0')
            engine=connection_planner.Evaluator(db,fixtures.NOW,False)
            edge=engine.edge(db.execute("SELECT id FROM ride_edge WHERE origin='A' AND destination='B'").fetchone()[0])
            duration,source=engine.costs.ride(edge,engine.schedule(edge)[0][1],fixtures.NOW.timestamp())
        self.assertEqual(duration,600);self.assertEqual(source['historical_segments'],0)

    def test_coordinate_anchor_includes_verified_access_time(self):
        with store.connection() as db:
            origin=store.get_stop(db,'A')
            anchor={**origin,'id':'A','lat':origin['lat']+.0001}
            foot={'available':True,'distance_meters':150,'geometry':[[anchor['lat'],anchor['lon']],[origin['lat'],origin['lon']]]}
            with patch.object(connection_adapter.walking,'route',return_value=foot) as route:
                access=materialized_adapter.Walks().route(anchor,origin,'boarding')
        self.assertEqual(access['seconds'],120)
        self.assertEqual(access['duration_minutes'],2)
        self.assertNotEqual(route.call_args.args[0]['id'],route.call_args.args[1]['id'])

    def test_http_progressive_contract_uses_new_planner(self):
        self.prepare_physical()
        with override_settings(SPTRANS_PLANNER='connections'),patch.object(graph,'graph_path',return_value=self.index),patch.object(connection_planner.realtime,'add_predictions',lambda row,stop:None),patch.object(connection_planner.timezone,'now',return_value=fixtures.NOW):
            response=self.client.get('/api/sptrans/board/',{'origin':'A','destination':'D','stream':'1','nearby':'1'})
            chunks=[json.loads(chunk) for chunk in response.streaming_content]
        self.assertEqual(response.status_code,200)
        self.assertEqual(chunks[-1]['planner'],'connections')
        self.assertTrue(chunks[-1]['complete'])
        self.assertEqual(chunks[-1]['journeys'][0]['duration_minutes'],40)
