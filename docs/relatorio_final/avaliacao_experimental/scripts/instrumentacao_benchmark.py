"""Hooks externos EXP-1. Não importa o aplicativo nem inicia consultas ao carregar.
Uso futuro exclusivo em processo isolado, sem concorrência, após piloto de compatibilidade.
"""
import copy, hashlib, json, time
from contextlib import contextmanager, ExitStack
from contextvars import ContextVar
from unittest.mock import patch

class FixtureMissing(RuntimeError):
    """Fatal: não pode virar ausência de rota nem buscar a rede."""

class FixtureStore:
    def __init__(self, entries):
        self.entries = copy.deepcopy(entries)
        self.used = []
    @staticmethod
    def key(namespace, request):
        return namespace + ':' + hashlib.sha256(json.dumps(request, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
    def get(self, namespace, request):
        key = self.key(namespace, request)
        if key not in self.entries:
            raise FixtureMissing('Fixture ausente: ' + key)
        self.used.append(key)
        entry = self.entries[key]
        if entry.get('outcome') == 'fixture_error':
            raise FixtureMissing('Erro técnico congelado: ' + key)
        if entry.get('outcome') != 'response':
            raise FixtureMissing('Envelope de fixture inválido: ' + key)
        return copy.deepcopy(entry['value'])


def signature(legs):
    # Ignora a caminhada para agrupar a sequência dirigida de ônibus; conserva
    # os caminhos de acesso/egresso em evidências de itinerários separadas.
    mapped = []
    for leg in legs:
        if leg.get('modo') not in (None, 'onibus'):
            continue
        def value(en, pt):
            if en in leg: return leg[en]
            if pt in leg: return leg[pt]
            raise ValueError('Trecho incompleto: ' + en)
        mapped.append(tuple(str(value(en, pt)) for en, pt in (
            ('origin', 'origem'), ('destination', 'destino'), ('pattern_id', 'padrao_id'),
            ('boarding_index', 'embarque_indice'), ('alighting_index', 'desembarque_indice'))))
    return tuple(mapped)

class Collector:
    def __init__(self):
        self.candidates = {}; self.events = []; self.fallback = False
    def observe(self, legs, stage, source=None, candidate_id=None):
        sig = signature(legs)
        if not sig: return None
        key = hashlib.sha256(json.dumps(sig).encode()).hexdigest()
        item = self.candidates.setdefault(key, {'signature':sig, 'sources':set(), 'stages':set(), 'ids':set()})
        if source: item['sources'].add(source)
        item['stages'].add(stage)
        if candidate_id: item['ids'].add(candidate_id)
        self.events.append({'candidate':key, 'stage':stage, 'source':source, 'monotonic':time.monotonic()})
        return key
    def export(self):
        return {'candidates':[{ 'key':k, **{f:sorted(v) if isinstance(v,set) else v for f,v in data.items()}} for k,data in self.candidates.items()], 'events':self.events, 'fallback_executed':self.fallback}

class CursorProxy:
    def __init__(self, cursor, observe): self.cursor,self.observe = cursor,observe
    def __iter__(self):
        for row in self.cursor: self.observe(row); yield row
    def fetchone(self):
        row=self.cursor.fetchone()
        if row is not None:self.observe(row)
        return row
    def fetchall(self):
        rows=self.cursor.fetchall()
        for row in rows:self.observe(row)
        return rows
    def fetchmany(self,*args):
        rows=self.cursor.fetchmany(*args)
        for row in rows:self.observe(row)
        return rows
    def __getattr__(self,name):return getattr(self.cursor,name)

class ConnectionProxy:
    def __init__(self, connection, collector):self.connection,self.collector=connection,collector
    def execute(self, sql, *args, **kwargs):
        cursor=self.connection.execute(sql,*args,**kwargs)
        if ' '.join(sql.split()) == 'SELECT * FROM direct_services WHERE origin=? AND destination=?':
            return CursorProxy(cursor,lambda row:self.collector.observe([dict(row)],'recuperado','indice_direto'))
        return cursor
    def __getattr__(self,name):return getattr(self.connection,name)

@contextmanager
def observe_sources(adapter, materialized, direct, collector):
    """Módulos explícitos, já carregados pelo controlador futuro. Patches restaurados."""
    phase=ContextVar('phase',default='auxiliar')
    old_prepare=adapter._prepare_materialized; old_expand=materialized._expand
    old_connection=direct.connection; old_evaluate=adapter.Evaluator.evaluate
    def prepare(*args,**kwargs):
        token=phase.set('consolidado')
        try:return old_prepare(*args,**kwargs)
        finally:phase.reset(token)
    def expand(row,source):
        result=old_expand(row,source)
        n=int(row['boardings'])
        label=('consolidado_'+str(n)) if phase.get()=='consolidado' else ('componentes_1' if n==1 else 'componentes_2_composicao_limitada')
        collector.observe(result['trechos'],'recuperado',label)
        return result
    @contextmanager
    def connection(*args,**kwargs):
        with old_connection(*args,**kwargs) as db:yield ConnectionProxy(db,collector)
    def evaluate(engine,candidate,*args,**kwargs):
        # preliminary já carrega essas arestas no caminho observado. Mesmo assim
        # contabilizar overhead deste hook, que não muda resultado/cotas/ordem.
        legs=[dict(engine.edge(e)) for e in json.loads(candidate['edge_ids'])]
        collector.observe(legs,'avaliado',candidate_id=candidate['id'])
        result=old_evaluate(engine,candidate,*args,**kwargs)
        if result[0]:collector.observe(legs,'aceito_pelo_avaliador_temporal',candidate_id=candidate['id'])
        return result
    with ExitStack() as stack:
        for obj,name,fn in [(adapter,'_prepare_materialized',prepare),(materialized,'_expand',expand),(direct,'connection',connection),(adapter.Evaluator,'evaluate',evaluate)]:
            stack.enter_context(patch.object(obj,name,fn))
        yield collector

@contextmanager
def select_variant(alternatives,settings,variant,collector):
    if variant not in ('A','B','C'):raise ValueError('Variante inválida')
    bus=alternatives._bus_progressive; rounds=alternatives._raptor_progressive
    def bounded_bus(*args,**kwargs):
        if variant=='A':kwargs['allow_raptor']=False
        yield from bus(*args,**kwargs)
    def rounds_observed(*args,**kwargs):
        if variant=='A':raise RuntimeError('Fallback proibido na variante A')
        if variant=='C':collector.fallback=True
        yield from rounds(*args,**kwargs)
    with patch.object(settings,'SPTRANS_PLANNER','raptor' if variant=='B' else 'connections',create=True), patch.object(alternatives,'_bus_progressive',bounded_bus), patch.object(alternatives,'_raptor_progressive',rounds_observed):
        yield

@contextmanager
def frozen_inputs(walking,client,timezone,instant,fixtures):
    if instant.tzinfo is None:raise ValueError('Instante precisa de fuso')
    def route(origin,destination,wait_for_slot=False):
        return fixtures.get('walking',{'origin':origin,'destination':destination,'wait_for_slot':wait_for_slot})
    def get(*args,**kwargs):return fixtures.get('olho_vivo',{'args':args,'kwargs':kwargs})
    with patch.object(walking,'route',route),patch.object(client,'get',get),patch.object(timezone,'now',lambda:instant):yield


def iter_variant(alternatives,settings,variant,collector,db,origin,destination,instant,*,gates):
    """Gerador para controlador futuro; não monta infraestrutura nem valida consentimento.
    Gabarito externo deve adjudicar saídas. Não chama isto nos testes do pacote.
    """
    needed=('isolamento_validado','rede_bloqueada','fixtures_completas','piloto_aprovado','procedencia_validada','fontes_conferidas')
    if any(gates.get(k) is not True for k in needed):raise RuntimeError('Pré-voo incompleto')
    if instant.tzinfo is None:raise ValueError('Instante sem fuso')
    with select_variant(alternatives,settings,variant,collector):
        for response in alternatives.progressive(db,origin,destination,max_transfers=1,now=instant,refresh=False):
            # Melhorias comuns de desembarque podem mudar assinatura. Não atribuir
            # procedência antiga à nova sequência por semelhança; vincular pelo id,
            # preservando ambos os estágios, e conferir no piloto.
            for j in response.get('journeys',[]):
                legs=j.get('legs',[])
                try:collector.observe(legs,'publicado_pipeline',candidate_id=j.get('id'))
                except ValueError:
                    collector.events.append({'stage':'publicado_assinatura_nao_mapeada','id':j.get('id')})
            yield response


def measure(generator,validate,collector):
    """Consome gerador lazy; adjudica SOMENTE após fim para não consumir os
    prazos internos dos planejadores. Supervisor externo impõe os 120 s.
    validate(journey) -> bool, por gabarito independente versionado.
    Não escreve arquivos. Cópias/eventos e seus custos integram o observador.
    """
    import resource
    start=time.monotonic();cpu=time.process_time();emissions=[]
    for response in generator:
        emissions.append({'emissao_s':time.monotonic()-start,'response':copy.deepcopy(response)})
    finish=time.monotonic()-start;cpu_s=time.process_time()-cpu
    rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    first=None;observations=[];last_valid=[];complete=False
    validation_start=time.monotonic()
    for emission in emissions:
        response=emission['response'];valid=[j for j in response.get('journeys',[]) if validate(j)]
        if valid and first is None:first=emission['emissao_s']
        complete=bool(response.get('complete'));last_valid=valid
        observations.append({'emissao_s':emission['emissao_s'],'complete':complete,'validas':len(valid),'itinerarios':valid})
    return {'status':'concluido' if complete else 'falha_tecnica','primeira_alternativa_s':first,'termino_s':finish,'validas':len(last_valid) if complete else None,'cpu_s':cpu_s,'rss_pico_kib':rss,'tempo_gabarito_s':time.monotonic()-validation_start,'fallback':collector.fallback,'observacoes':observations,'emissoes_brutas':emissions}
