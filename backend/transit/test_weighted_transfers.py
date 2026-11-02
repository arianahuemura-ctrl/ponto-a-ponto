import csv
import tempfile
from pathlib import Path
from unittest.mock import patch
from django.test import SimpleTestCase, override_settings
from transit.sptrans import planner, store, transfer_policy, alternatives
from transit.test_rail import NOW


class WeightedTransferTests(SimpleTestCase):
    def network(self, services):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        rows = {table: [] for table in store.TABLES}
        ids = sorted({s for _, _, stops, _ in services for s in stops})
        rows['stops'] = [[sid, sid, '', -23.5 - i * .02, -46.6] for i, sid in enumerate(ids)]
        rows['calendar'] = [['daily', 1, 1, 1, 1, 1, 1, 1, '20260101', '20261231']]
        for code, kind, stops, seconds in services:
            rows['routes'].append([code, '1', code, code, kind, '005cec'])
            rows['trips'].append([code, 'daily', code, 'Destino', '0', 'S'])
            for i, sid in enumerate(stops):
                at = 7 * 3600 + i * seconds
                clock = f'{at//3600:02}:{at//60%60:02}:{at%60:02}'
                rows['stop_times'].append([code, clock, clock, sid, i + 1])
            rows['frequencies'].append([code, '04:00:00', '24:00:00', 120, '0'])
        for table in rows:
            with (root / (table + '.txt')).open('w') as f:
                writer=csv.writer(f); writer.writerow(store.TABLES[table]); writer.writerows(rows[table])
        path = root / 'network.sqlite3'; store.import_gtfs(root, path)
        override = override_settings(SPTRANS_DATABASE=path, SPTRANS_TOKEN='', SPTRANS_PLANNER='raptor')
        override.enable(); self.addCleanup(override.disable)
        planner._network.cache_clear(); planner._nearby.cache_clear()

    def chain(self, kinds):
        self.network([(f'L{i}', kind, [str(i), str(i+1)], 60) for i, kind in enumerate(kinds)])

    def plan(self, origin, destination, ceiling=4, **kwargs):
        with store.connection() as db:
            return planner.journeys(db, origin, destination, ceiling, NOW,
                                    include_rail=True, weighted_transfers=True, **kwargs)

    def test_twelve_internal_transfers_fit_four_but_thirteen_do_not(self):
        self.chain(['1', '2'] * 7)
        result = self.plan('0', '13')[0]
        self.assertEqual(result['transfers'], 12)
        self.assertEqual(result['transfer_cost_units'], 12)
        self.assertEqual(result['transfer_cost'], 4)
        self.assertEqual(self.plan('0', '14'), [])

    def test_four_bus_transfers_fit_and_five_do_not(self):
        self.chain(['3'] * 6)
        result = self.plan('0', '5')[0]
        self.assertEqual(result['transfer_cost'], 4)
        self.assertEqual(result['transfers'], 4)
        self.assertEqual(self.plan('0', '6'), [])

    def test_first_boarding_free_and_same_train_stations_not_transfers(self):
        self.network([('L1', '1', ['a', 'b', 'c', 'd'], 60)])
        result = self.plan('a', 'd', 0)[0]
        self.assertEqual(result['transfer_cost'], 0)
        self.assertEqual(result['transfers'], 0)
        self.assertEqual(len(result['legs'][0]['stops']), 4)

    def test_bus_rail_mixed_budget_preserves_actual_waits(self):
        self.chain(['3'] + ['1'] * 7 + ['3'])
        result = self.plan('0', '9')[0]
        self.assertEqual(result['transfers'], 8)
        self.assertEqual(result['transfer_cost'], 4)
        # 9 rides of 1 minute, 9 waits of 1 minute and 8 buffers of 2 minutes.
        self.assertEqual(result['duration_minutes'], 34)

    def test_internal_interchange_discount_is_not_given_to_external_walk(self):
        self.network([('A', '1', ['a', 'b'], 60), ('B', '2', ['c', 'd'], 60)])
        with store.connection() as db:
            b, c = store.get_stop(db, 'b'), store.get_stop(db, 'c')
        for internal, expected in [(True, 1), (False, 3)]:
            foot = {'available': True, 'internal_transfer': internal, 'seconds': 120,
                    'distance_meters': 100, 'origin': b, 'destination': c}
            with patch.object(planner, '_nearby', return_value={'b': [('c', 100)]}):
                result = self.plan('a', 'd', 1, transfer_paths={('b','c'): foot}, known_transfers_only=True)[0]
            self.assertEqual(result['transfer_cost_units'], expected)
            self.assertEqual(result['duration_minutes'], 8)

    def test_slower_cheaper_prefix_survives_faster_expensive_prefix(self):
        self.network([('SLOW', '1', ['a','c'], 1200), ('FAST1','3',['a','b'],60),
                      ('FAST2','3',['b','c'],60), ('END','1',['c','d'],60)])
        results = self.plan('a','d', 1)
        self.assertTrue(any([l['code'] for l in j['legs']] == ['SLOW','END'] for j in results))
        self.assertTrue(all(j['transfer_cost_units'] <= 3 for j in results))

    def test_internal_access_before_first_train_is_not_a_transfer(self):
        self.network([('L1','1',['b','c'],60),('ACCESS','1',['a','x'],60)])
        with store.connection() as db:
            a,b = store.get_stop(db,'a'),store.get_stop(db,'b')
        foot={'internal_transfer':True,'available':True,'seconds':120,'distance_meters':0,'origin':a,'destination':b}
        with patch.object(planner,'_nearby',return_value={'a':[('b',0)]}):
            result=self.plan('a','c',0,transfer_paths={('a','b'):foot},known_transfers_only=True)[0]
        self.assertEqual(result['transfer_cost_units'],0)
        self.assertEqual(result['access_stop_id'],'a')
        self.assertEqual(result['duration_minutes'],4)

    def test_minimum_plus_one_boundary_is_exact_in_thirds(self):
        def journey(identifier, modes):
            return {'id':identifier,'legs':[{'mode':m,'origin':{'id':str(i)},'destination':{'id':str(i+1)}} for i,m in enumerate(modes)]}
        rows=[journey('minimum',['metro','rail']), journey('boundary',['metro','rail','bus']),
              journey('over',['metro','rail','metro','bus'])]
        result,policy=transfer_policy.select(rows)
        self.assertEqual([j['id'] for j in result],['minimum','boundary'])
        self.assertEqual(policy['minimum_found'],1/3)
        self.assertEqual(policy['maximum_allowed'],4/3)

    def test_http_default_accepts_four_cost_and_reports_actual_twelve_transfers(self):
        self.chain(['1'] * 13)
        with patch('transit.sptrans.planner.timezone.localtime',return_value=NOW):
            response=self.client.get('/api/sptrans/board/',{'origin':'0','destination':'13','route_only':1})
        self.assertEqual(response.status_code,200)
        data=response.json()
        self.assertEqual(data['max_transfers'],4)
        self.assertEqual(data['journeys'][0]['transfers'],12)
        self.assertEqual(data['transfer_policy']['maximum_allowed'],4)

    def test_exhausted_search_does_not_claim_an_empty_network(self):
        self.chain(['1'] * 3)
        context={'weighted_deadline':0}
        self.assertEqual(self.plan('0','3',context=context),[])
        self.assertTrue(context['weighted_search_limited'])

    def test_five_slots_prefer_minimum_and_only_fill_remainder_with_extra_cost(self):
        def route(name,modes,minutes):
            return {'id':name,'duration_minutes':minutes,'legs':[{'mode':m,'origin':{'id':str(i)},
                    'destination':{'id':str(i+1)}} for i,m in enumerate(modes)]}
        minimum=[route(f'min{i}',['bus','bus'],50+i) for i in range(3)]
        extra=[route(f'extra{i}',['bus','bus','bus'],10+i) for i in range(4)]
        result,policy=transfer_policy.select(extra+minimum)
        self.assertEqual([j['id'] for j in result],['min0','min1','min2','extra0','extra1'])
        self.assertEqual(policy['max_routes'],5)
        minimum += [route('min3',['bus','bus'],53),route('min4',['bus','bus'],54)]
        result,_=transfer_policy.select(extra+minimum)
        self.assertEqual([j['id'] for j in result],['min0','min1','min2','min3','min4'])

    def test_slots_compare_weighted_cost_not_physical_transfers(self):
        def route(name,modes):
            return {'id':name,'duration_minutes':10,'legs':[{'mode':m,'origin':{'id':str(i)},
                    'destination':{'id':str(i+1)}} for i,m in enumerate(modes)]}
        rail=[route(f'rail{i}',['metro','rail','metro']) for i in range(5)]
        bus=route('bus',['bus','bus'])
        result,policy=transfer_policy.select([bus,*rail])
        self.assertEqual([j['id'] for j in result],[f'rail{i}' for i in range(5)])
        self.assertEqual(policy['minimum_found'],2/3)
        self.assertTrue(all(j['transfers']==2 for j in result))

    def test_progressive_replaces_higher_cost_slots_when_minimum_routes_arrive(self):
        def route(name,modes):
            return {'id':name,'duration_minutes':10,'walking_meters':0,'walks':[],'transfers':len(modes)-1,
                    'legs':[{'mode':mode,'code':name+str(i),'trip_id':name+str(i),'headsign':'Destino',
                             'origin':{'id':str(i)},'destination':{'id':str(i+1)}} for i,mode in enumerate(modes)]}
        high=[route(f'bus{i}',['bus','bus']) for i in range(5)]
        low=[route(f'rail{i}',['metro','rail']) for i in range(5)]
        snapshots=iter([{'journeys':high,'complete':False},{'journeys':high+low,'complete':True}])
        with patch.object(alternatives,'_multimodal_progressive',return_value=snapshots),\
             patch('transit.sptrans.journey_completion.direct_walk',return_value=None),\
             patch('transit.sptrans.journey_completion.Completion.improve',side_effect=lambda j:j):
            result=list(alternatives.progressive(None,{},{}))
        self.assertEqual([j['id'] for j in result[0]['journeys']],[f'bus{i}' for i in range(5)])
        self.assertEqual([j['id'] for j in result[-1]['journeys']],[f'rail{i}' for i in range(5)])
        self.assertEqual(result[-1]['transfer_policy']['minimum_found'],1/3)
