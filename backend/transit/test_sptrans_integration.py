import json
import sqlite3
from datetime import timedelta
from unittest.mock import patch
from django.test import SimpleTestCase, override_settings
from transit import test_sptrans_graph as fixtures
from transit.sptrans import (alternatives, catalog, city_connections, direct, graph,
                            materialized_adapter as adapter, materialized_connections as materialized,
                            connection_adapter, connection_planner, store, walking)


class MaterializedAppTests(SimpleTestCase):
    def setUp(self):
        fixtures.GraphTests.setUp(self)
        catalog.install(self.index)
        self.dp=self.root/'direct.sqlite3';self.cp=self.root/'components.sqlite3'
        self.mp=materialized.database_path()
        self.addCleanup(patch.stopall)
        patch.object(graph,'graph_path',return_value=self.index).start()
        patch.object(connection_planner.realtime,'add_predictions',lambda row,stop:None).start()
        self.mode=override_settings(SPTRANS_PLANNER='connections')
        self.mode.enable();self.addCleanup(self.mode.disable)

    def build(self, pairs=(('A','D'),)):
        direct.build(source=self.index,target=self.dp)
        city_connections.build(source=self.dp,graph_source=self.index,target=self.cp)
        materialized.materialize(pairs,source=self.cp,target=self.mp,min_free_bytes=0)

    @staticmethod
    def foot(a,b,**kw):
        return {'available':True,'distance_meters':150,
                'geometry':[[a['lat'],a['lon']],[b['lat'],b['lon']]]}

    def run_app(self, origin=None, destination=None, now=fixtures.NOW, **kw):
        with store.connection() as db:
            return list(alternatives._bus_progressive(db,origin or store.get_stop(db,'A'),
                        destination or store.get_stop(db,'D'),now=now,**kw))

    def anchors(self):
        with store.connection() as db:
            a=store.get_stop(db,'A');b=store.get_stop(db,'D')
        return ({**a,'id':'passenger-location','lat':a['lat']+.0001},
                {**b,'id':'address-to','lat':b['lat']+.0001})

    def test_physical_paths_use_both_walks_without_online_composition_or_fallback(self):
        self.build();a,b=self.anchors()
        originals={p:p.read_bytes() for p in (self.index,self.mp,self.cp)}
        with patch.object(walking,'route',side_effect=self.foot), \
             patch.object(city_connections,'structural_query',side_effect=AssertionError('online composition')), \
             patch.object(alternatives,'_raptor_progressive',side_effect=AssertionError('unexpected fallback')):
            result=self.run_app(a,b,now=fixtures.NOW-timedelta(minutes=5))[-1]
        self.assertEqual(result['planner'],'connections')
        best=result['journeys'][0]
        self.assertEqual(best['duration_minutes'],62)
        self.assertEqual(best['walking_meters'],300)
        self.assertEqual(best['walking_minutes'],4)
        self.assertEqual([w['accessType'] for w in best['walks']],['boarding','destination'])
        self.assertEqual(best['walks'][0]['origin']['id'],'passenger-location')
        self.assertEqual(best['walks'][-1]['destination']['id'],'address-to')
        for p,contents in originals.items():self.assertEqual(p.read_bytes(),contents)

    def test_no_routes_triggers_fallback_and_keeps_refresh(self):
        self.build()
        # A caminhada perde todas as primeiras partidas das 08:00. O fluxo novo vazio não deve fechar a interface.
        a,b=self.anchors()
        fallback={'journeys':[{'id':'old'}],'complete':True}
        with patch.object(walking,'route',side_effect=self.foot), \
             patch.object(alternatives,'_raptor_progressive',return_value=iter([fallback])) as old:
            chunks=self.run_app(a,b,refresh=True)
        self.assertEqual(chunks[-1]['planner'],'raptor')
        self.assertEqual(chunks[-1]['journeys'],[{'id':'old'}])
        self.assertTrue(chunks[-1]['planner_fallback'])
        self.assertTrue(old.call_args.kwargs['refresh'])
        self.assertEqual(sum(c['complete'] for c in chunks),1)

    def test_missing_and_stale_artifacts_fall_back(self):
        fallback={'journeys':[],'complete':True}
        with patch.object(alternatives,'_raptor_progressive',return_value=iter([fallback])) as old:
            self.assertEqual(self.run_app()[-1]['planner'],'raptor');old.assert_called_once()
        self.build()
        with sqlite3.connect(self.cp) as db:db.execute('CREATE TABLE modified(x)')
        with patch.object(alternatives,'_raptor_progressive',return_value=iter([fallback])) as old:
            self.assertEqual(self.run_app()[-1]['planner'],'raptor');old.assert_called_once()

    def test_unavailable_or_overlong_walk_is_not_published(self):
        self.build();a,b=self.anchors()
        for response in ({'available':False}, {'available':True,'distance_meters':1001,'geometry':[[0,0],[1,1]]}):
            with self.subTest(response=response), patch.object(walking,'route',return_value=response), \
                 patch.object(alternatives,'_raptor_progressive',return_value=iter([{'journeys':[],'complete':True}])) as old:
                chunks=self.run_app(a,b,now=fixtures.NOW-timedelta(minutes=5))
                self.assertTrue(all(not c['journeys'] for c in chunks));old.assert_called_once()

    def test_forecast_before_access_is_rejected_and_later_bus_kept(self):
        self.build();a,b=self.anchors()
        def predictions(row,stop):
            if row['code']=='DIRECT':
                row['arrivals']=[{'time':t,'vehicle':t,'observed_at':fixtures.NOW.isoformat()}
                                 for t in ('08:01','08:05')]
        with patch.object(walking,'route',side_effect=self.foot), \
             patch.object(connection_planner.realtime,'add_predictions',side_effect=predictions):
            result=self.run_app(a,b)[-1]
        self.assertEqual(result['planner'],'connections')
        self.assertEqual(len(result['journeys']),1)
        leg=result['journeys'][0]['legs'][0]
        self.assertEqual(leg['timing_source'],'olho_vivo')
        self.assertIn('08:05:00',leg['departure'])
        self.assertEqual(result['journeys'][0]['duration_minutes'],67)

    def test_final_artifact_walk_is_replaced_not_added_twice(self):
        with sqlite3.connect(self.index) as db:
            db.execute("UPDATE walk_edge SET status='verified',distance_meters=75,seconds=60 WHERE origin='B' AND destination='E'")
        self.build((('A','E'),))
        with store.connection() as db:destination=store.get_stop(db,'E')
        with patch.object(walking,'route',side_effect=self.foot), \
             patch.object(alternatives,'_raptor_progressive',side_effect=AssertionError('fallback')):
            result=self.run_app(destination=destination)[-1]
        best=result['journeys'][0]
        self.assertEqual(best['walking_meters'],150)
        self.assertEqual(best['walking_minutes'],2)
        self.assertEqual(best['duration_minutes'],12)
        self.assertEqual(len(best['walks']),1)
        self.assertEqual(best['walks'][0]['origin']['id'],'B')
        self.assertEqual(best['walks'][0]['destination']['id'],'E')

    def test_intermediate_walk_without_stored_geometry_is_verified(self):
        with sqlite3.connect(self.index) as db:
            db.execute("UPDATE walk_edge SET status='verified',distance_meters=75,seconds=60 WHERE origin='B' AND destination='E'")
        self.build((('A','C'),))
        with patch.object(walking,'route',side_effect=self.foot):
            with store.connection() as db:
                destination=store.get_stop(db,'C')
            journeys=self.run_app(destination=destination)[-1]['journeys']
        item=next(j for j in journeys if any(l['code']=='E1' for l in j['legs']))
        self.assertEqual(item['transfer_walk_seconds'],120)
        self.assertEqual(item['walking_meters'],150)
        self.assertEqual(item['walks'][0]['before_leg'],1)
        self.assertTrue(item['walks'][0]['geometry'])

    def test_http_contract_gps_access_and_egress(self):
        self.build();a,b=self.anchors()
        with patch.object(walking,'route',side_effect=self.foot), \
             patch.object(alternatives.timezone,'now',return_value=fixtures.NOW-timedelta(minutes=5)):
            response=self.client.get('/api/sptrans/board/',{'origin':'passenger-location','destination':'D',
                'from_lat':a['lat'],'from_lon':a['lon'],'to_lat':b['lat'],'to_lon':b['lon'],'stream':'1','nearby':'1'})
            chunks=[json.loads(c) for c in response.streaming_content]
        self.assertEqual(response.status_code,200)
        self.assertEqual(chunks[-1]['planner'],'connections')
        self.assertEqual(chunks[-1]['journeys'][0]['walking_meters'],150)
        self.assertEqual(chunks[-1]['journeys'][0]['mode'],'walk')
        # Neste fixture, caminhar diretamente custa menos que o acesso e saída do ônibus.
        self.assertTrue(all(not j['legs'] for j in chunks[-1]['journeys']))
        self.assertEqual(chunks[-1]['selected_journey'],chunks[-1]['journeys'][0]['id'])

    def test_materialized_dispatch_caps_boardings_but_raptor_keeps_three(self):
        ready={'journeys':[{'id':'two-buses'}],'complete':True}
        with patch.object(connection_adapter,'prepare',return_value={'paths':[]}), \
             patch.object(connection_adapter,'progressive',return_value=iter([ready])) as prepared, \
             patch.object(alternatives,'_raptor_progressive') as fallback:
            self.run_app(max_transfers=2)
        self.assertEqual(prepared.call_args.args[3],1)
        fallback.assert_not_called()
        empty={'journeys':[],'complete':True}
        with patch.object(connection_adapter,'prepare',return_value={'paths':[]}), \
             patch.object(connection_adapter,'progressive',return_value=iter([empty])), \
             patch.object(alternatives,'_raptor_progressive',return_value=iter([ready])) as fallback:
            result=self.run_app(max_transfers=2)[-1]
        self.assertEqual(result['planner'],'raptor')
        self.assertEqual(fallback.call_args.args[3],2)

    def test_invalid_artifact_exposes_fallback_reason(self):
        self.build()
        with store.connection() as db, \
             patch.object(materialized,'_validate',side_effect=ValueError('Conexões materializadas desatualizadas')), \
             patch.object(alternatives,'_raptor_progressive',return_value=iter([{'journeys':[],'complete':True}])):
            result=list(alternatives._bus_progressive(db,store.get_stop(db,'A'),store.get_stop(db,'D'),now=fixtures.NOW))[-1]
        self.assertEqual(result['planner'],'raptor')
        self.assertEqual(result['planner_fallback'],'Conexões materializadas desatualizadas')

    def test_direct_index_is_used_without_materialized_pair(self):
        self.build()
        with patch.object(direct,'database_path',return_value=self.dp), \
             patch.object(adapter,'_prepare_materialized',return_value=None), \
             patch.object(walking,'route',side_effect=self.foot), \
             patch.object(alternatives,'_raptor_progressive',side_effect=AssertionError('RAPTOR não deve ser consultado')):
            with store.connection() as db:
                origin=store.get_stop(db,'A')
                destination=store.get_stop(db,'B')
                context=adapter.prepare(db,origin,destination)
                self.assertTrue(context['paths'])
                result=list(alternatives._bus_progressive(db,origin,destination,now=fixtures.NOW))[-1]
            self.assertEqual(result['planner'],'connections')
            self.assertTrue(result['journeys'])
            self.assertTrue(all(len(j['legs'])==1 for j in result['journeys']))

    def test_preprocessed_final_walk_without_materialized_pair(self):
        with sqlite3.connect(self.index) as db:
            db.execute("UPDATE walk_edge SET status='verified',distance_meters=75,seconds=60 WHERE origin='B' AND destination='E'")
        self.build()
        with patch.object(direct,'database_path',return_value=self.dp), \
             patch.object(city_connections,'database_path',return_value=self.cp), \
             patch.object(adapter,'_prepare_materialized',return_value=None):
            with store.connection() as db:
                context=adapter.prepare(db,store.get_stop(db,'A'),store.get_stop(db,'E'))
        self.assertTrue(context['paths'])
        self.assertTrue(any(p['trechos'][-1]['modo']=='caminhada' for p in context['paths']))
        self.assertTrue(all(sum(l['modo']=='onibus' for l in p['trechos'])==1 for p in context['paths']))

    def test_two_bus_fallback_without_consolidated_pair(self):
        self.build()
        with patch.object(direct,'database_path',return_value=self.dp), \
             patch.object(city_connections,'database_path',return_value=self.cp), \
             patch.object(adapter,'_prepare_materialized',return_value=None):
            with store.connection() as db:
                context=adapter.prepare(db,store.get_stop(db,'A'),store.get_stop(db,'D'))
        self.assertTrue(any(sum(l['modo']=='onibus' for l in p['trechos'])==2 for p in context['paths']))
