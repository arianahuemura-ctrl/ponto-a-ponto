from django.test import SimpleTestCase
from transit.sptrans.experimental_pruning import sampled_convergence
from transit.test_sptrans_city_connections import CityConnectionsTests


class ConvergenceTests(SimpleTestCase):
    def test_approaching_and_equal_are_preserved(self):
        self.assertTrue(sampled_convergence([(0,1),(0,0)],(0,2),(0,0)))
        self.assertTrue(sampled_convergence([(0,-2),(0,3)],(0,2),(0,0)))
    def test_both_samples_away_are_pruned(self):
        self.assertFalse(sampled_convergence([(0,3),(0,4)],(0,2),(0,0)))
    def test_missing_coordinates_preserve_branch(self):
        self.assertTrue(sampled_convergence([None,(0,4)],(0,2),(0,0)))
    def test_sampling_can_miss_an_intermediate_approach(self):
        # Documenta a perda deliberada: a primeira parada se aproxima, as amostras não.
        self.assertFalse(sampled_convergence([(0,0),(0,3),(0,4)],(0,2),(0,0)))


class ExperimentalQueryTests(CityConnectionsTests):
    def test_three_is_policy_skipped_when_original_has_two(self):
        original=self.query()
        self.assertTrue(any(p['embarques']<=2 for p in original['trajetos']))
        result=self.query(experimental=True)
        self.assertTrue(result['categories'][3]['policy_skipped'])
        self.assertFalse(any(p['embarques']==3 for p in result['trajetos']))
        self.assertNotIn('experimental_policy',self.query())
    def test_no_connection_is_not_marked_as_policy_skip(self):
        result=self.query('D','A',experimental=True)
        self.assertFalse(result['categories'][3]['policy_skipped'])

    def test_geographic_pruning_is_not_published_as_no_route_in_reference(self):
        from unittest.mock import patch
        with patch('transit.sptrans.experimental_pruning.sampled_convergence',return_value=False):
            result=self.query(experimental=True)
        self.assertFalse(result['trajetos'])
        self.assertGreater(result['convergence_stats']['sequences_pruned'],0)
        self.assertTrue(self.query()['trajetos'])

    def test_comparison_command_is_reproducible_and_readonly(self):
        import json
        from io import StringIO
        from django.core.management import call_command
        pairs=self.root/'pairs.json';pairs.write_text(json.dumps([['A','D']]))
        from transit.sptrans import catalog
        catalog.install(self.index)
        before=self.cp.read_bytes()
        output=StringIO()
        call_command('compare_sptrans_heuristics',pairs_file=str(pairs),source=str(self.cp),
                     graph=str(self.index),at='2026-10-08T08:00:00-03:00',stdout=output)
        result=json.loads(output.getvalue())
        self.assertFalse(result['operational'])
        self.assertEqual(len(result['results']),1)
        self.assertEqual(before,self.cp.read_bytes())
