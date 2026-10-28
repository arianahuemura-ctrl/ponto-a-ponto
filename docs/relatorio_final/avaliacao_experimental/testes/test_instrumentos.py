"""Somente dados ARTIFICIAIS em memória/tmp; não importa o app nem acessa bancos."""
import sys,unittest,tempfile,copy,json,types
from pathlib import Path
from contextlib import contextmanager
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from analisar import analyze,metrics,describe,distributions
from segmentar import segment
from agregar_telemetria import aggregate
from manifesto import inventory
from prontidao import missing
from resumir_benchmark import summarize
from instrumentacao_benchmark import FixtureStore,FixtureMissing,Collector,observe_sources,select_variant,measure

def row(condition='MAN'):
    return dict(participante_pseudonimo='ARTIFICIAL_P01',cenario_id='ARTIFICIAL_C01',tarefa='T2',escopo='T6_acesso_T2_planejamento',condicao=condition,conclusao='sucesso_sem_ajuda',comparavel='sim',experimento_id='ARTIFICIAL',gabarito_revisao='TEST',versao_build='TEST',dispositivo='TEST',dataset_hash='TEST',partida_fixa='TEST',ordem='MAN_QR',periodo='1' if condition=='MAN' else '2',toques='3',longos='0',rolagens='1',arrastos='0',t0='0',to='1',td='2',ta='3',tc='',ts='4',tf='5',SEQ_1_7='5',compreensao_baldeacao='nao_aplicavel')
def event(seq,kind='context',elapsed=None,**extra):
    return dict(session_alias='S001',epoch=0,seq=seq,elapsed_ms=seq*1000 if elapsed is None else elapsed,kind=kind,**extra)

class Paired(unittest.TestCase):
    def test_scroll_equals_tap_and_missing_tc_not_exclude(self):
        m,q=row(),row('QR');q['toques']='1'
        pairs,summary,eff,ex=analyze([m,q]);self.assertFalse(ex)
        self.assertEqual(metrics(m)['acoes'],4)
        self.assertTrue(any(r['metrica']=='tf_s' for r in pairs))
        self.assertFalse(any(r['metrica']=='tc_s' for r in pairs))
        self.assertEqual(next(r for r in pairs if r['metrica']=='acoes')['diferenca_QR_MAN'],-2)
    def test_failure_kept_efficiency_excluded(self):
        m,q=row(),row('QR');q.update(conclusao='limite_tempo',tf='')
        pairs,_,eff,ex=analyze([m,q]);self.assertFalse(pairs)
        self.assertTrue(any(r['conclusao']=='limite_tempo' for r in eff));self.assertTrue(ex)
    def test_context_mismatch(self):
        q=row('QR');q['dataset_hash']='OTHER';self.assertFalse(analyze([row(),q])[0])
    def test_duplicate_rejected(self):
        with self.assertRaises(ValueError):analyze([row(),row()])
    def test_negative_or_bad_seq(self):
        for field,val in [('tf','-1'),('SEQ_1_7','8'),('toques','1.5')]:
            r=row();r[field]=val
            with self.assertRaises(ValueError):metrics(r)
    def test_progressive_choice_before_completion(self):
        r=row();r['tc']='8';self.assertEqual(metrics(r)['tc_s'],8)
    def test_type7(self):
        self.assertEqual(describe([1,2,3,4])['iqr'],1.5);self.assertIsNone(describe([1])['iqr'])
    def test_seq_and_comprehension_include_failure(self):
        r=row();r['conclusao']='falha';a,b=distributions([r]);self.assertEqual(next(x for x in b if x['condicao']=='MAN' and x['SEQ_1_7']==5)['n'],1)
        x=next(x for x in a if x['condicao']=='MAN' and x['item']=='baldeacao' and x['classificacao']=='nao_aplicavel');self.assertEqual(x['n'],1);self.assertEqual(x['denominador_aplicavel'],0)

class Segmentation(unittest.TestCase):
    def test_context_then_planning_one_attempt(self):
        r=segment([event(1,origin_alias='L1',destination_alias='L2'),event(2,'planning_explicit'),event(3,'api_result',association='confirmed',has_alternatives=True)])
        self.assertEqual(len(r),1);self.assertEqual(r[0]['alternativa_resposta_ms'],3000)
    def test_intent_not_confirmed(self):
        r=segment([event(1,origin_alias='L1',destination_alias='L2'),event(2,'cancel_intent')]);self.assertEqual(r[0]['encerramento'],'fim_observacao_nao_abandono')
        r=segment([event(1,origin_alias='L1',destination_alias='L2'),event(2,'cancel_confirmed')]);self.assertEqual(r[0]['encerramento'],'cancelamento_confirmado')
    def test_requery_and_inactivity(self):
        r=segment([event(1,'planning_explicit'),event(2,'api_result'),event(3,'planning_explicit'),event(4,'api_result',elapsed=200000)])
        self.assertEqual(len(r),3);self.assertTrue(any(x['encerramento']=='lacuna_inatividade_nao_abandono' for x in r))
        self.assertTrue(all(x['dificuldade']=='nao_inferida' for x in r))
    def test_auto_selection_and_raw_pii_rejected(self):
        for e in [event(1,'journey'),event(1,query='PRIVATE')]:
            with self.assertRaises(ValueError):segment([e])
    def test_epochs_and_ambiguous_response(self):
        e=event(2,'api_result',elapsed=1);e['epoch']=1
        r=segment([event(1,'api_result',association='ambiguous',has_alternatives=True),e]);self.assertEqual(len(r),2);self.assertIsNone(r[0]['alternativa_resposta_ms'])
    def test_no_aggregate_from_one_session_many_attempts(self):
        attempts=segment([event(1,'planning_explicit')])*10;self.assertEqual(aggregate(attempts)['tentativas'],'suprimido')
    def test_suppression_complement(self):
        base=segment([event(1,'planning_explicit')])[0];rows=[]
        for i in range(6):
            r=copy.deepcopy(base);r['session_alias']=f'S{i:03}';r['erros_tecnicos']=int(i<5);rows.append(r)
        self.assertEqual(aggregate(rows)['tentativas_com_erros_tecnicos'],'suprimido')

class Provenance(unittest.TestCase):
    def leg(self):return dict(origin='O',destination='D',pattern_id='P',boarding_index=0,alighting_index=1)
    def test_fixture_no_network_and_copy(self):
        key=FixtureStore.key('test',{'a':1});s=FixtureStore({key:{'outcome':'response','value':{'x':[]}}})
        value=s.get('test',{'a':1});value['x'].append(2);self.assertEqual(s.get('test',{'a':1}),{'x':[]})
        with self.assertRaises(FixtureMissing):s.get('test',{'a':2})
    def test_merge_provenance(self):
        c=Collector();c.observe([self.leg()],'recuperado','consolidado_1');c.observe([self.leg()],'recuperado','indice_direto')
        out=c.export();self.assertEqual(len(out['candidates']),1);self.assertEqual(len(out['candidates'][0]['sources']),2)
    def test_hooks_preserve_results_and_restore(self):
        leg=self.leg();path={'trechos':[leg]}
        class Engine:
            def edge(self,e):return leg
            def evaluate(self,candidate,*args,**kwargs):return {'ok':True},'evaluated'
        materialized=types.SimpleNamespace(_expand=lambda row,db:copy.deepcopy(path))
        adapter=types.SimpleNamespace(Evaluator=Engine)
        adapter._prepare_materialized=lambda *args:materialized._expand({'boardings':1},None)
        @contextmanager
        def connection(*a):yield None
        direct=types.SimpleNamespace(connection=connection);orig=materialized._expand;orig_eval=Engine.evaluate;c=Collector()
        with observe_sources(adapter,materialized,direct,c):
            self.assertEqual(adapter._prepare_materialized(),path)
            materialized._expand({'boardings':2},None)
            self.assertEqual(Engine().evaluate({'id':'test','edge_ids':'[1]'}),({'ok':True},'evaluated'))
        self.assertIs(materialized._expand,orig);self.assertIs(Engine.evaluate,orig_eval)
        sources=c.export()['candidates'][0]['sources'];self.assertIn('consolidado_1',sources);self.assertIn('componentes_2_composicao_limitada',sources)
    def test_abc_fallback_observed_and_restore(self):
        settings=types.SimpleNamespace(SPTRANS_PLANNER='original');a=types.SimpleNamespace()
        a._raptor_progressive=lambda *args,**kwargs:iter([{'result':'rounds'}])
        def bus(*args,allow_raptor=True,**kwargs):
            if allow_raptor:yield from a._raptor_progressive()
        a._bus_progressive=bus
        for variant,expected in [('A',False),('B',False),('C',True)]:
            c=Collector()
            with select_variant(a,settings,variant,c):
                results=list(a._bus_progressive());self.assertEqual(c.fallback,expected)
                if variant=='A':self.assertEqual(results,[])
            self.assertEqual(settings.SPTRANS_PLANNER,'original')
    def test_measure_requires_completion(self):
        r=measure(iter([{'journeys':[{'id':'test'}],'complete':False}]),lambda j:True,Collector())
        self.assertEqual(r['status'],'falha_tecnica');self.assertIsNone(r['validas'])

class Integrity(unittest.TestCase):
    def test_manifest(self):
        with tempfile.TemporaryDirectory(prefix='ARTIFICIAL-PAP-') as d:
            p=Path(d);(p/'raw.txt').write_text('ARTIFICIAL');(p/'link').symlink_to(p/'raw.txt')
            self.assertEqual(inventory(p,['raw.txt'])[0]['bytes'],10)
            for path in ['../raw.txt','link']:
                with self.assertRaises(ValueError):inventory(p,[path])
    def test_empty_readiness_blocks(self):self.assertTrue(missing({}))
    def test_benchmark_timeout_not_success_latency(self):
        base=dict(execucao_id='ARTIFICIAL_1',cenario_id='TEST',variante='C',cache='frio',status='concluido',validas='1',termino_s='4',primeira_alternativa_s='2',cpu_s='1',rss_pico_kib='10',fallback='sim')
        timeout={**base,'execucao_id':'ARTIFICIAL_2','status':'timeout','validas':'','termino_s':'120','fallback':''}
        data=summarize([base,timeout]);item=next(x for x in data if x['metrica']=='termino_s')
        self.assertEqual(item['n_tentativas'],2);self.assertEqual(item['mediana'],4);self.assertEqual(item['n_timeouts'],1);self.assertEqual(item['fallback_denominador'],1)

if __name__=='__main__':unittest.main()
