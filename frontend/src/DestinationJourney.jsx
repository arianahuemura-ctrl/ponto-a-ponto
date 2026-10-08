import {humanDuration} from './duration.js';
import {useEffect,useState} from 'react';
import {api} from './api.js';
export default function DestinationJourney({origin,destination,onJourney,onStatus,onClear}) {
  const [result,setResult]=useState(null),[error,setError]=useState(''),[retry,setRetry]=useState(0);
  useEffect(()=>{
    setResult(null);setError('');onJourney(null);
    if(!origin||!destination||origin.id===destination.id){onStatus('idle');return;}
    onStatus('loading');
    const abort=new AbortController();
    api('sptrans/board',{origin:origin.id,destination:destination.id,max_transfers:2},abort.signal).then(data=>{
      if(!abort.signal.aborted){setResult(data);onJourney(data.journeys?.[0]||null);onStatus(data.journeys?.length?'ready':'empty');}
    }).catch(e=>{if(!abort.signal.aborted){setError(e.message);onStatus('error');}});
    return()=>abort.abort();
  },[origin?.id,destination?.id,retry,onJourney,onStatus]);
  if(!destination)return null;
  const journey=result?.journeys?.[0];
  return <section className="sp-route-card" aria-label="Rota para o destino">
    <button className="text-button" onClick={onClear} aria-label="Limpar destino">×</button>
    <strong>{destination.destinationAddress||destination.name}</strong>
    <p>Desembarque: {destination.name} · ponto {destination.id}</p>
    {destination.addressDistance!=null&&<small>Parada a {destination.addressDistance} m do endereço em linha reta. O trajeto calculado termina na parada.</small>}
    {!origin?<p>Selecione no mapa seu ponto de partida para calcular a rota.</p>:origin.id===destination.id?<p>Você já está na parada mais próxima do destino.</p>:<>
      {!result&&!error&&<p role="status">Calculando rota…</p>}
      {error&&<p role="alert">{error} <button className="text-button" onClick={()=>setRetry(n=>n+1)}>Tentar novamente</button></p>}
      {result&&!journey&&<p>Nenhuma viagem encontrada até esta parada nas próximas 6 horas, com até 2 trocas.</p>}
      {journey&&<><p><strong>Cerca de {humanDuration(journey.duration_minutes)}</strong> · {journey.transfers?`${journey.transfers} troca(s)`:'Sem trocas'}</p>
        <details><summary>Como chegar</summary><ol>{journey.legs.map((leg,i)=><li key={i}><strong>{leg.code} · {leg.headsign}</strong><p>{leg.origin.name} → {leg.destination.name}</p></li>)}</ol>
        <p>Estimativa GTFS com espera média. Não é previsão ao vivo. Traçado esquemático entre paradas; até 2 trocas no mesmo ponto.</p></details></>}
    </>}
  </section>;
}
