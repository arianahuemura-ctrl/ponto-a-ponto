import {useEffect,useRef,useState} from 'react';
import {api,apiProgressive} from './api.js';
import Icon from './Icon.jsx';
import {boardingCoordinates} from './location.js';
const time=value=>new Date(value).toLocaleTimeString('pt-BR',{hour:'2-digit',minute:'2-digit',timeZone:'America/Sao_Paulo'});
export default function BoardDialog({passengerPosition,open,requestId,active,onStatus,origin,destination,onClose,onDestination,onCancel,onFavorite,isFavorite,onJourney,onChooseJourney}) {
  const dialog=useRef(),chosenTrip=useRef(null),forceSearch=useRef(false);
  const latestPosition=useRef(passengerPosition),planningAnchor=useRef(null);
  useEffect(()=>{latestPosition.current=passengerPosition;},[passengerPosition]);
  const [chosen,setChosen]=useState(null),[expanded,setExpanded]=useState(false);
  useEffect(()=>{setChosen(null);chosenTrip.current=null;setExpanded(false);},[origin?.id,destination?.id]);
  const [showInfo,setShowInfo]=useState(false),[pointLink,setPointLink]=useState(''),[infoError,setInfoError]=useState('');
  useEffect(()=>{setShowInfo(false);setPointLink('');setInfoError('');},[origin?.id,open]);
  useEffect(()=>{
    if(!showInfo||!origin)return;
    const abort=new AbortController();setPointLink('');setInfoError('');
    api('sptrans/qr/'+encodeURIComponent(origin.id),{format:'json'},abort.signal).then(result=>{if(!abort.signal.aborted)setPointLink(result.url);}).catch(()=>{if(!abort.signal.aborted)setInfoError('Não foi possível carregar as informações do ponto.');});
    return()=>abort.abort();
  },[showInfo,origin?.id]);
  const [data,setData]=useState(null),[error,setError]=useState(''),[busy,setBusy]=useState(false),[tick,setTick]=useState(0);
  useEffect(()=>{const element=dialog.current;if(open&&origin){if(!element.open)element.showModal();}else if(element.open)element.close();},[open,origin?.id,requestId]);
  useEffect(()=>{if(destination||!open||busy)return;const timer=setInterval(()=>{if(!document.hidden)setTick(v=>v+1);},30000);return()=>clearInterval(timer);},[open,busy,destination?.id]);
  useEffect(()=>{
    if(!origin||!active)return;
    const coordinates=boardingCoordinates(latestPosition.current,origin);
    const anchorKey=JSON.stringify([origin.id,destination?.id,coordinates]);
    if(planningAnchor.current!==anchorKey){
      planningAnchor.current=anchorKey;chosenTrip.current=null;setChosen(null);setData(null);onJourney(null);
    }
    const abort=new AbortController();setError('');setBusy(true);onStatus(destination?'Calculando rota…':'');
    const refresh=forceSearch.current;forceSearch.current=false;
    apiProgressive('sptrans/board',{origin:origin.id,...(refresh?{refresh:1}:{}),...(destination?{destination:destination.id,route_only:1,nearby:1,stream:1,max_transfers:2,...(chosenTrip.current?{journey:chosenTrip.current.id}:{}),...coordinates,...(destination.addressCoordinates?{to_lat:destination.addressCoordinates.lat,to_lon:destination.addressCoordinates.lon}:{})}:{})},abort.signal,result=>{
      if(abort.signal.aborted)return;
      const sameBoardings=route=>JSON.stringify(route.legs.map((leg,index)=>[leg.trip_id,leg.origin.id,index<route.legs.length-1?leg.destination.id:null]));
      let previous=chosenTrip.current;
      const service=leg=>JSON.stringify([leg.route_id||leg.code,leg.direction_id??leg.trip_id,leg.headsign]);
      const dominated=previous&&result.journeys?.some(other=>other.legs.length<previous.legs.length&&other.legs.every((leg,i)=>service(leg)===service(previous.legs[i]))&&other.duration_minutes<=previous.duration_minutes&&other.walking_meters<=previous.walking_meters);
      if(dominated){previous=null;chosenTrip.current=null;setChosen(null);}

      const improved=previous&&result.journeys?.find(j=>sameBoardings(j)===sameBoardings(previous)&&j.duration_minutes<=previous.duration_minutes);
      let trip=improved||result.journeys?.find(j=>j.id===previous?.id)||previous||result.journeys?.find(j=>j.id===result.selected_journey)||result.journeys?.[0]||null;
      if(chosenTrip.current&&trip){
        chosenTrip.current=trip;setChosen(trip.id);
        if(!result.journeys.some(j=>j.id===trip.id))result={...result,journeys:[...result.journeys,trip].sort((a,b)=>a.duration_minutes-b.duration_minutes)};
        if(trip.id!==result.selected_journey)result={...result,selected_journey:trip.id,lines:trip.legs.map(l=>({...l,arrivals:[],planned_departure:l.departure}))};
      }
      setData({...result,key:origin.id+':'+(destination?.id||'')});onJourney(trip);
      onStatus(result.complete===false?'Buscando outras alternativas…':destination&&!result.journeys?.length?'Nenhuma rota disponível para os pontos e horário selecionados.':'');
    })
      .catch(e=>{if(!abort.signal.aborted){setError(e.message);onStatus(e.message);}})
      .finally(()=>{if(!abort.signal.aborted)setBusy(false);});
    return()=>abort.abort();
  },[active,origin?.id,destination?.id,origin?.addressCoordinates?.lat,origin?.addressCoordinates?.lon,origin?.manualBoarding,destination?.addressCoordinates?.lat,destination?.addressCoordinates?.lon,tick,onJourney,onStatus]);
  const current=data?.key===origin?.id+':'+(destination?.id||'')?data:null;
  const selected=current?.journeys?.find(j=>j.id===chosen)||current?.journeys?.find(j=>j.id===current.selected_journey)||current?.journeys?.[0];
  const chooseJourney=trip=>{chosenTrip.current=trip;setChosen(trip.id);onJourney(trip);setData(previous=>({...previous,selected_journey:trip.id,lines:trip.legs.map(l=>({...l,arrivals:[],planned_departure:l.departure}))}));onChooseJourney();onClose();};
  return <dialog ref={dialog} className="sp-stop-dialog sp-board-dialog" aria-labelledby="board-title" onCancel={e=>{e.preventDefault();onClose();}}>
    <header className="sp-board-top"><div className="sp-board-title"><h2 id="board-title">{destination?'Ônibus da sua rota':'Próximos ônibus'}</h2>{!origin?.useLocation&&<button type="button" className="icon-button sp-point-info-toggle" aria-label="Informações do ponto" title="Informações do ponto" aria-expanded={showInfo} aria-controls="sp-point-info" onClick={()=>setShowInfo(value=>!value)}><Icon name="info"/></button>}</div><div className="sp-board-window-actions"><button className="icon-button" onClick={onClose} aria-label="Ver mapa" title="Ver mapa"><Icon name="map"/></button><button className="icon-button" onClick={onCancel} aria-label="Cancelar viagem" title="Cancelar viagem"><Icon name="close"/></button></div></header>
    {showInfo&&<section id="sp-point-info" className="sp-point-info" aria-label="QR Code e endereço do ponto"><h3>{origin?.name} · {origin?.id}</h3>{infoError?<p role="alert">{infoError}</p>:pointLink?<><img src={'/api/sptrans/qr/'+encodeURIComponent(origin.id)+'/'} alt={'QR Code do ponto '+origin.id} onError={()=>setInfoError('Não foi possível carregar o QR Code. Tente abrir as informações novamente.')}/><a href={pointLink}>{pointLink}</a></>:<p role="status">Carregando QR Code…</p>}</section>}
    <p><strong>Embarque:</strong> {selected?.legs[0]?.origin.name||origin?.name}{(selected||!origin?.useLocation)&&<> · {selected?.legs[0]?.origin.id||origin?.id}</>}</p>
    {destination&&<p><strong>Destino:</strong> {destination.destinationAddress||destination.name} · parada {destination.id}</p>}
    {(!destination||!origin?.useLocation)&&<div className="sp-board-actions">{!destination&&<button className="primary" onClick={onDestination}>Selecionar destino</button>}
      {!origin?.useLocation&&<button className="icon-button sp-favorite-action" onClick={onFavorite} aria-label={isFavorite?'Remover favorito':'Adicionar embarque aos favoritos'} title={isFavorite?'Remover favorito':'Adicionar aos favoritos'} data-saved={isFavorite}><Icon name="star"/></button>}
      </div>}
    {destination&&current?.journeys?.length>0&&<section className="sp-route-options" aria-label="Alternativas de viagem"><h3>{expanded?'Rotas calculadas':'Rotas mais rápidas'}</h3>{(expanded?current.journeys:current.journeys.slice(0,3)).map((trip,index)=><button type="button" className="sp-route-option" key={trip.id||index} aria-pressed={selected===trip} onClick={()=>chooseJourney(trip)}><strong>{index+1}. {trip.duration_minutes} min · {trip.transfers||0} baldeações</strong><span>{trip.legs.map(l=>l.code).join(' → ')}</span><small>{trip.walking_meters||0} m a pé · {trip.walking_minutes||0} min de caminhada</small>{trip.arrival&&<span className="sp-route-arrival"><small>Chegada estimada</small><strong>{time(trip.arrival)}</strong></span>}</button>)}{current.journeys.length>3&&<button className="text-button" onClick={()=>setExpanded(v=>!v)}>{expanded?'Mostrar apenas as três mais rápidas':`Mostrar todas as ${current.journeys.length} rotas calculadas`}</button>}</section>}
    {selected?.walks?.length>0&&<section aria-label="Caminhadas da rota">{selected.walks.map((w,i)=><p key={i}>A pé {w.accessType==='boarding'?'até o embarque':w.accessType==='destination'?'até o destino':`na baldeação ${w.before_leg}`}: {w.distance_meters} m · {w.duration_minutes} min{w.accessType==='transfer'?` · ${w.origin.name} → ${w.destination.name}`:''}</p>)}</section>}
    <div className="sp-board-refresh"><button className="icon-button" aria-label={busy?(destination?'Carregando rotas':'Carregando horários'):destination?'Reiniciar busca':'Atualizar horários'} title={busy?(destination?'Carregando rotas':'Carregando horários'):destination?'Reiniciar busca':'Atualizar horários'} aria-busy={busy} disabled={busy} onClick={()=>{forceSearch.current=!!destination;if(destination){chosenTrip.current=null;setChosen(null);setExpanded(false);setData(null);onJourney(null);}setTick(v=>v+1);}}><Icon name={busy?'hourglass':'refresh'} className={busy?'sp-loading-hourglass':undefined}/></button>{current?.queried_at&&<small>Consulta às {time(current.queried_at)}{!destination&&' · atualização a cada 30 s'}</small>}</div>
    {busy&&<p role="status">{destination?"Buscando alternativas… As rotas aparecem conforme são calculadas e a ordem ainda pode mudar.":"Consultando próximos ônibus…"}</p>}
    {error&&<p role="alert">{error}</p>}
    {current?.warning&&<p className="sp-warning">Informações em tempo real indisponíveis. Os horários apresentados são estimativas baseadas na programação das linhas.</p>}
    {current&&current.complete!==false&&!current.lines?.length&&<p>{current.search_limited?'Nenhuma rota verificada antes do limite de cálculo. Tente atualizar.':origin?.id===destination?.id?'Origem e destino são o mesmo ponto.':destination?'Nenhuma rota encontrada nas próximas 6 horas com até 2 trocas.':'Nenhuma linha programada encontrada para este ponto.'}</p>}
    {!destination&&<div className="sp-lines">{current?.lines?.map((line,index)=><article key={line.trip_id+':'+index}>
      <h3>{line.code} · {line.headsign}</h3>
      {line.origin&&<p>Embarque: {line.origin.name} · {line.origin.id}<br/>Desembarque: {line.destination.name} · {line.destination.id}</p>}
      {line.arrivals?.length?<><p className="sp-live">Próximas chegadas · SPTrans</p><ul>{line.arrivals.slice(0,5).map((arrival,i)=><li key={i}><strong>{arrival.time}</strong> · veículo {arrival.vehicle}{arrival.accessible?' · acessível':''}</li>)}</ul></>:<p>Estimativa baseada nos horários programados, sem atualização em tempo real.</p>}
      {line.planned_departure&&<p>Embarque estimado no planejamento: {time(line.planned_departure)} (horário programado; não é previsão em tempo real).</p>}
      {line.programme?.map((p,i)=><p key={i}>{p.kind==='frequency'?`Intervalo programado: ${p.interval_minutes} min · ${time(p.start)}–${time(p.end)}`:`Horário programado: ${time(p.start)}`}</p>)}
    </article>)}</div>}
  </dialog>;
}
