import {useJourneyForecast,operationalArrival} from './useJourneyForecast.js';
import PointControl from './PointControl.jsx';
import {useCallback,useEffect,useRef,useState} from 'react';
import {api,apiProgressive} from './api.js';
import Icon from './Icon.jsx';
import SelectableBusLine from './SelectableBusLine.jsx';
import {useApproachingBus} from './useApproachingBus.js';
import {boardingMinutes, liveArrivals, humanBoarding, orderedBoardLines} from './boardingTime.js';
import {mergeProgramme} from './programme.js';
import {boardingCoordinates} from './location.js';
const time=value=>new Date(value).toLocaleTimeString('pt-BR',{hour:'2-digit',minute:'2-digit',timeZone:'America/Sao_Paulo'});
function BoardingCountdown({trip,selected,boardingLive,active,clock,onArrival}) {
  const accessMinutes=(trip.walks||[]).filter(w=>w.accessType==='boarding').reduce((sum,w)=>sum+(Number(w.duration_minutes)||0),0);
  const live=useApproachingBus(trip.legs[0],active&&!selected,accessMinutes);
  const current=selected?boardingLive:live;
  const minutes=boardingMinutes(current?.arrivals,clock,accessMinutes);
  const next=liveArrivals(current?.arrivals,clock,accessMinutes)[0];
  const forecasts=useJourneyForecast(trip,active);
  const transferArrival=trip.legs.length>1?operationalArrival(trip,{...forecasts,0:current},clock,accessMinutes):null;
  const remaining=Date.parse(trip.arrival)-Date.parse(trip.legs[0]?.departure);
  const updatedArrival=next&&trip.legs.length===1&&Number.isFinite(remaining)&&remaining>=0?next.expected+remaining:transferArrival;
  const orderingArrival=updatedArrival!==null?updatedArrival:next?Infinity:Date.parse(trip.arrival);
  useEffect(()=>{onArrival(trip,orderingArrival);},[trip,orderingArrival,onArrival]);
  return <>
    <small>Caminhada até o embarque: {accessMinutes.toLocaleString('pt-BR',{maximumFractionDigits:1})} min</small>
    {minutes===null?<small className="sp-boarding-status">{!current?'Consultando embarque…':current.noReachableArrival||current.arrivals?.length?'Sem previsão compatível com a caminhada':'Previsão de embarque indisponível'}</small>:<span className="sp-boarding-countdown" title="Previsão de chegada ao embarque · SPTrans"><strong>Embarque em {minutes} min</strong></span>}
    {next&&<small>Embarque previsto às {time(next.expected)} · SPTrans</small>}
    <span className="sp-route-arrival"><small>{updatedArrival!==null?'Chegada ao destino · estimativa atualizada':'Chegada ao destino · planejamento'}</small>
      {updatedArrival!==null?<><strong>{time(updatedArrival)}</strong><small>{Math.max(0,Math.ceil((updatedArrival-clock)/60000))} min a partir de agora</small><small>Tempos dentro dos ônibus baseados no planejamento</small></>:<><strong>{time(trip.arrival)}</strong>{next&&<small>Aguardando previsões compatíveis para todos os trechos. Horário acima corresponde ao planejamento.</small>}</>}
    </span>
  </>;
}

export default function BoardDialog({onWatchLines,onWatchBus,boardingLive,passengerPosition,open,requestId,active,onStatus,origin,destination,onClose,onDestination,onCancel,onFavorite,isFavorite,onJourney,onChooseJourney}) {
  const [arrivalTimes,setArrivalTimes]=useState({});
  const reportArrival=useCallback((trip,value)=>setArrivalTimes(previous=>{
    if(previous[trip.id]?.trip===trip&&Object.is(previous[trip.id]?.value,value))return previous;
    return {...previous,[trip.id]:{trip,value}};
  }),[]);
  useEffect(()=>setArrivalTimes({}),[origin?.id,destination?.id]);
  const [lineOrder,setLineOrder]=useState('arrival');
  const [routeOrder,setRouteOrder]=useState('fastest');
  const [markedLines,setMarkedLines]=useState({});
  const [selectingLines,setSelectingLines]=useState(false);
  useEffect(()=>{setMarkedLines({});setSelectingLines(false);},[origin?.id,destination?.id]);
  const selectLine=line=>{setSelectingLines(true);setMarkedLines(previous=>{const next={...previous};if(next[line.trip_id])delete next[line.trip_id];else next[line.trip_id]={trip_id:line.trip_id,code:line.code,headsign:line.headsign,origin};return next;});};
  const returnMap=()=>{if(!destination&&selectingLines)onWatchLines(Object.values(markedLines));else onClose();};
  const dialog=useRef(),chosenTrip=useRef(null),forceSearch=useRef(false),backdropPress=useRef(null);
  const outsidePanel=event=>{
    const box=event.currentTarget.getBoundingClientRect();
    return event.clientX<box.left||event.clientX>box.right||event.clientY<box.top||event.clientY>box.bottom;
  };
  const pressBackdrop=event=>{backdropPress.current=event.isPrimary&&event.button===0&&outsidePanel(event)?{x:event.clientX,y:event.clientY}:null;};
  const moveBackdrop=event=>{const start=backdropPress.current;if(start&&Math.hypot(event.clientX-start.x,event.clientY-start.y)>10)backdropPress.current=null;};
  const clickBackdrop=event=>{
    const start=backdropPress.current;backdropPress.current=null;
    if(!start||!outsidePanel(event))return;
    event.preventDefault();event.stopPropagation();returnMap();
  };
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
      result={...result,journeys:result.journeys?.map(trip=>({...trip,planner:trip.planner||result.planner}))};
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
  const [clock,setClock]=useState(Date.now);
  useEffect(()=>{if(!open)return;setClock(Date.now());const timer=setInterval(()=>setClock(Date.now()),1000);return()=>clearInterval(timer);},[open]);
  const arrivalOrder=trip=>{
    if(trip.mode==='walk')return clock+trip.duration_minutes*60000;
    const update=arrivalTimes[trip.id];
    const value=update?.trip===trip?update.value:Date.parse(trip.arrival);
    return Number.isFinite(value)&&value>=clock?value:Infinity;
  };
  const orderedJourneys=[...(current?.journeys||[])].sort((a,b)=>{
    const preference=routeOrder==='transfers'?(a.transfers||0)-(b.transfers||0):routeOrder==='walking'?(a.walking_meters||0)-(b.walking_meters||0):0;
    return preference||arrivalOrder(a)-arrivalOrder(b)||a.duration_minutes-b.duration_minutes||String(a.id).localeCompare(String(b.id));
  });
  const chooseJourney=trip=>{chosenTrip.current=trip;setChosen(trip.id);onJourney(trip);setData(previous=>({...previous,selected_journey:trip.id,lines:trip.legs.map(l=>({...l,arrivals:[],planned_departure:l.departure}))}));onChooseJourney();onClose();};
  return <dialog ref={dialog} className="sp-stop-dialog sp-board-dialog" aria-labelledby="board-title" onPointerDown={pressBackdrop} onPointerMove={moveBackdrop} onPointerCancel={()=>{backdropPress.current=null;}} onClick={clickBackdrop} onCancel={e=>{e.preventDefault();returnMap();}}>
    <header className="sp-board-top"><div className="sp-board-title"><h2 id="board-title">{destination?'Ônibus da sua rota':'Próximos ônibus'}</h2>{!origin?.useLocation&&<button type="button" className="icon-button sp-point-info-toggle" aria-label="Informações do ponto" title="Informações do ponto" aria-expanded={showInfo} aria-controls="sp-point-info" onClick={()=>setShowInfo(value=>!value)}><Icon name="info"/></button>}</div><div className="sp-board-window-actions"><button className="icon-button" onClick={returnMap} aria-label="Ver mapa" title="Ver mapa"><Icon name="map"/></button><button className="icon-button" onClick={onCancel} aria-label={destination?'Cancelar viagem':'Desmarcar embarque'} title={destination?'Cancelar viagem':'Desmarcar embarque'}><Icon name="close"/></button></div></header>
    {showInfo&&<section id="sp-point-info" className="sp-point-info" aria-label="QR Code e endereço do ponto"><h3>{origin?.name} · {origin?.id}</h3>{infoError?<p role="alert">{infoError}</p>:pointLink?<><img src={'/api/sptrans/qr/'+encodeURIComponent(origin.id)+'/'} alt={'QR Code do ponto '+origin.id} onError={()=>setInfoError('Não foi possível carregar o QR Code. Tente abrir as informações novamente.')}/><a href={pointLink}>{pointLink}</a></>:<p role="status">Carregando QR Code…</p>}</section>}
    <p><strong>{selected?.mode==='walk'?'Origem:':'Embarque:'}</strong> {selected?.legs[0]?.origin.name||origin?.name}{(selected||!origin?.useLocation)&&<> · {selected?.legs[0]?.origin.id||origin?.id}</>}</p>
    {destination&&<p><strong>Destino:</strong> {destination.destinationAddress||destination.name} · parada {destination.id}</p>}
    <div className="sp-board-actions"><PointControl kind="destination" point={destination} onClick={onDestination}/>
      {(destination||!origin?.useLocation)&&<button className="text-button sp-favorite-action" onClick={onFavorite} aria-label={isFavorite?'Remover favorito':'Adicionar ponto aos favoritos'} title={isFavorite?'Remover favorito':'Adicionar ponto aos favoritos'} aria-pressed={isFavorite} data-saved={isFavorite}><Icon name="star"/><span>{isFavorite?'Ponto favorito':'Salvar ponto'}</span></button>}
    </div>
    {destination&&current?.journeys?.length>0&&<section className="sp-route-options" aria-label="Alternativas de viagem"><h3>Alternativas de viagem</h3><label className="sp-board-order">Ordenar rotas por <select aria-label="Ordenar rotas por" value={routeOrder} onChange={e=>setRouteOrder(e.target.value)}><option value="fastest">Mais rápido</option><option value="transfers">Menos baldeações</option><option value="walking">Menos caminhada</option></select></label>{orderedJourneys.map((trip,index)=><button type="button" className="sp-route-option" key={trip.id||index} aria-pressed={selected===trip} onClick={()=>chooseJourney(trip)}><strong>{index+1}. {trip.duration_minutes} min no planejamento · {trip.mode==='walk'?'Somente a pé':`${trip.transfers||0} baldeações`}{trip.mode!=='walk'&&trip.planner==='raptor'&&<span className="sp-raptor-mark" role="img" aria-label="Rota calculada pelo RAPTOR" title="Rota calculada pelo RAPTOR"><Icon name="eagle"/></span>}</strong><span>{trip.legs.map(l=>l.code).join(' → ')}</span><small>{trip.walking_meters||0} m a pé · {trip.walking_minutes||0} min de caminhada total</small>{trip.mode!=='walk'&&<BoardingCountdown trip={trip} selected={selected===trip} boardingLive={boardingLive} active={open&&active} clock={clock} onArrival={reportArrival}/>}{trip.mode==='walk'&&trip.arrival&&<span className="sp-route-arrival"><small>Chegada ao destino · planejamento</small><strong>{time(clock+trip.duration_minutes*60000)}</strong></span>}</button>)}{false&&current.journeys.length>3&&<button className="text-button" onClick={()=>setExpanded(v=>!v)}>{expanded?'Mostrar apenas as três mais rápidas':`Mostrar todas as ${current.journeys.length} rotas calculadas`}</button>}</section>}
    {selected?.walks?.length>0&&<section aria-label="Caminhadas da rota">{selected.walks.map((w,i)=><p key={i}>A pé {w.accessType==='boarding'?'até o embarque':w.accessType==='destination'?'até o destino':`na baldeação ${w.before_leg}`}: {w.distance_meters} m · {w.duration_minutes} min{w.accessType==='transfer'?` · ${w.origin.name} → ${w.destination.name}`:''}</p>)}</section>}
    <div className="sp-board-refresh"><button className="icon-button" aria-label={busy?(destination?'Carregando rotas':'Carregando horários'):destination?'Reiniciar busca':'Atualizar horários'} title={busy?(destination?'Carregando rotas':'Carregando horários'):destination?'Reiniciar busca':'Atualizar horários'} aria-busy={busy} disabled={busy} onClick={()=>{forceSearch.current=!!destination;if(destination){chosenTrip.current=null;setChosen(null);setExpanded(false);setData(null);onJourney(null);}setTick(v=>v+1);}}><Icon name={busy?'hourglass':'refresh'} className={busy?'sp-loading-hourglass':undefined}/></button>{current?.queried_at&&<small>Consulta às {time(current.queried_at)}{!destination&&' · atualização a cada 30 s'}</small>}</div>
    {busy&&<p role="status">{destination?"Buscando alternativas… As rotas aparecem conforme são calculadas e a ordem ainda pode mudar.":"Consultando próximos ônibus…"}</p>}
    {error&&<p role="alert">{error}</p>}
    {current?.warning&&<p className="sp-warning">Informações em tempo real indisponíveis. Os horários apresentados são estimativas baseadas na programação das linhas.</p>}
    {current&&current.complete!==false&&!current.lines?.length&&!current.journeys?.length&&<p>{current.search_limited?'Nenhuma rota verificada antes do limite de cálculo. Tente atualizar.':origin?.id===destination?.id?'Origem e destino são o mesmo ponto.':destination?'Nenhuma rota encontrada nas próximas 6 horas com até 2 trocas.':'Nenhuma linha programada encontrada para este ponto.'}</p>}
    {!destination&&<label className="sp-board-order">Ordenar por <select value={lineOrder} onChange={e=>setLineOrder(e.target.value)}><option value="arrival">Próximos ônibus</option><option value="alphabetical">Nome do destino (A–Z)</option><option value="number">Número da linha</option></select></label>}
    {!destination&&<div className="sp-multi-actions">{selectingLines?<><span>{Object.keys(markedLines).length} linhas selecionadas</span><button className="text-button" onClick={()=>{setSelectingLines(false);setMarkedLines({});}}>Limpar seleção</button></>:<button className="text-button" onClick={()=>setSelectingLines(true)}>Selecionar linhas para acompanhar</button>}</div>}
    {!destination&&<div className="sp-lines">{orderedBoardLines(current?.lines,clock,lineOrder).map((line,index)=><SelectableBusLine key={line.trip_id||index} line={line} selecting={selectingLines} checked={!!markedLines[line.trip_id]} onSelect={selectLine} onWatch={line=>onWatchLines([{...line,origin}])}>
      <h3>{line.code} · {line.headsign}</h3>
      {line.origin&&<p>Embarque: {line.origin.name} · {line.origin.id}<br/>Desembarque: {line.destination.name} · {line.destination.id}</p>}
      {line.live.length?<div className="sp-next-arrivals"><small>Previsão de chegada · SPTrans</small><ul>{line.live.slice(0,5).map((arrival,i)=><li key={arrival.vehicle+':'+i}><strong className="sp-next-countdown">{humanBoarding(arrival.seconds)}</strong><button type="button" className="sp-watch-bus" onClick={()=>onWatchBus({...line,origin,vehicle:String(arrival.vehicle)})} aria-label={`Ver veículo ${arrival.vehicle} da linha ${line.code} no mapa`}><span>Ver ônibus no mapa →</span></button><span>No veículo {arrival.vehicle}{arrival.accessible?' — acessível':''}</span><small>Chegada prevista às {arrival.time}</small></li>)}</ul></div>:<p>Previsão de chegada indisponível. Consulte os horários ou frequências programados abaixo.</p>}

      {line.planned_departure&&<p>Embarque estimado no planejamento: {time(line.planned_departure)} (horário programado; não é previsão em tempo real).</p>}
      {!line.live.length&&mergeProgramme(line.programme).map((p,i)=><p key={i}>{p.kind==='frequency'?`A cada ${p.interval_minutes} min, das ${time(p.start)} às ${time(p.end)}`:`Horário programado: ${time(p.start)}`}</p>)}
    </SelectableBusLine>)}</div>}
  </dialog>;
}
