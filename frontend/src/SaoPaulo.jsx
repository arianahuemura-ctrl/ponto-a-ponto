import FullscreenButton from './FullscreenButton.jsx';
import {record,trace} from './usability.js';
import FavoritesDialog from './FavoritesDialog.jsx';
import PointControl from './PointControl.jsx';
import appIcon from '../../icone.png';
import {useEffect,useState,useRef,useMemo} from 'react';
import {api} from './api.js';
import {useApproachingLines} from './useApproachingLines.js';
import {useApproachingBus} from './useApproachingBus.js';
import {locationOrigin, withLocationParams} from './location.js';
import {usePassengerLocation} from './usePassengerLocation.js';
import {useMapStops} from './useMapStops.js';
import {useTheme} from './useTheme.js';
import {readSession,readFavorites,favoriteStop,save,sessionKey,favoritesKey} from './spSession.js';
import SaoPauloMap from './SaoPauloMap.jsx';
import Icon from './Icon.jsx';
import DestinationSearch from './DestinationSearch.jsx';
import BoardDialog from './BoardDialog.jsx';
import FavoriteNameDialog from './FavoriteNameDialog.jsx';
import RemoveFavoriteDialog from './RemoveFavoriteDialog.jsx';
import CancelTripDialog from './CancelTripDialog.jsx';
import './sao-paulo.css';
const ignorePreviewJourney=()=>{};
function initialSession(){try{return readSession(sessionStorage,location.search);}catch{return {origin:null,destination:null};}}
function initialFavorites(){try{return readFavorites(localStorage);}catch{return [];}}
export default function SaoPaulo(){
  const {resolvedTheme,setTheme}=useTheme();
  const {position:passengerPosition,error:locationError}=usePassengerLocation();
  const [session,setSession]=useState(initialSession),[favorites,setFavorites]=useState(initialFavorites);
  const [previewStop,setPreviewStop]=useState(null);
  const [editingFavorite,setEditingFavorite]=useState(null),[removingFavorite,setRemovingFavorite]=useState(null);
  const [boardRequest,setBoardRequest]=useState(0);
  const [highlightStopsRequest,setHighlightStopsRequest]=useState(0);
  const [cancelRequested,setCancelRequested]=useState(false);
  const [manualOrigin,setManualOrigin]=useState(false);
  const [preserveViewport,setPreserveViewport]=useState(false);
  const openBoard=()=>{setDestinationSearch(false);setView('navigate');setMode('board');setBoardRequest(n=>n+1);};
  const [center,setCenter]=useState({lat:-23.5505,lon:-46.6333}),[viewport,setViewport]=useState(null);
  const [view,setView]=useState('navigate'),[mode,setMode]=useState(()=>new URLSearchParams(location.search).get('stop')?'board':session.origin?(session.destination?'map':'destination'):'origin'),[notice,setNotice]=useState('');
  const [destinationSearch,setDestinationSearch]=useState(false),[searchRole,setSearchRole]=useState(()=>session.origin?'destination':'origin'),[journey,setJourney]=useState(null);
  const [planningStatus,setPlanningStatus]=useState('');
  useEffect(()=>{record('state',{mode,view,origin:!!session.origin,destination:!!session.destination,gps:!!passengerPosition});},[mode,view,!!session.origin,!!session.destination,!!passengerPosition]);
  const [watchedBus,setWatchedBus]=useState(null);
  const [watchedLines,setWatchedLines]=useState([]);
  useEffect(()=>setWatchedLines([]),[session.origin?.id,session.destination?.id]);
  const lineTracking=useApproachingLines(watchedLines,mode==='watch'&&view==='navigate');
  const lineItineraries=useMemo(()=>lineTracking?.filter(l=>l.itinerary).map(l=>({...l.itinerary,trip_id:l.trip_id,code:l.code}))||[],[lineTracking]);
  const lineApproaches=useMemo(()=>lineTracking?.flatMap(l=>[...(l.approaches||[l.approach]),...(l.passedApproaches||[])]).filter(Boolean)||[],[lineTracking]);
  useEffect(()=>{if(mode!=='watch')setWatchedBus(null);},[mode,session.origin?.id,session.destination?.id]);
  const routeSelected=!!session.origin&&!!session.destination&&mode!=='destination'&&mode!=='origin';
  const selectingPoint=mode==='origin'||mode==='destination';
  const {stops,loading:searching,error:searchError}=useMapStops(selectingPoint&&view==='navigate'?viewport:null);
  const {origin,destination}=session;
  const [streetView,setStreetView]=useState(null);
  const [walks,setWalks]=useState([]),[walkWarning,setWalkWarning]=useState('');
  const [selectedLeg,setSelectedLeg]=useState(null);
  const [mapFocus,setMapFocus]=useState(0);
  const [passengerFocus,setPassengerFocus]=useState(null);
  const [coordinateFocus,setCoordinateFocus]=useState(null);
  useEffect(()=>trace('app_state',{mode,view,session,passengerPosition,favorites,journey,selectedLeg,destinationSearch,searchRole,notice}),[mode,view,session,passengerPosition,favorites,journey,selectedLeg,destinationSearch,searchRole,notice]);
  const leg=selectedLeg===null?null:journey?.legs[selectedLeg];
  const trackingLeg=routeSelected?(mode==='board'?journey?.legs[0]:(leg||journey?.legs[0])):(mode==='watch'?watchedBus:null);
  const boardingWalkMinutes=(journey?.walks||walks).filter(w=>w.accessType==='boarding').reduce((sum,w)=>sum+(Number(w.duration_minutes)||0),0);
  const trackingIndex=journey?.legs.indexOf(trackingLeg)??0;
  const transferMinutes=(journey?.walks||walks).filter(w=>w.accessType==='transfer'&&w.before_leg===trackingIndex).reduce((sum,w)=>sum+(Number(w.duration_minutes)||0),0);
  const previousArrival=Date.parse(journey?.legs[trackingIndex-1]?.arrival);
  const earliestBoarding=trackingIndex>0&&Number.isFinite(previousArrival)?new Date(previousArrival+(transferMinutes+2)*60000).toISOString():null;
  const liveBus=useApproachingBus(trackingLeg,view==='navigate',boardingWalkMinutes,earliestBoarding);
  const shownJourney=useMemo(()=>leg?{...journey,legs:[leg]}:journey,[journey,leg]);
  const shownWalks=useMemo(()=>!leg?walks:walks.filter(path=>(path.accessType==='boarding'&&selectedLeg===0)||(path.accessType==='destination'&&selectedLeg===journey.legs.length-1)||(path.accessType==='transfer'&&(path.before_leg===selectedLeg||path.before_leg===selectedLeg+1))),[leg,walks,selectedLeg,journey]);
  const itinerary=journey?.legs.map((l,i)=>`${l.trip_id}:${l.origin.id}:${i<journey.legs.length-1?l.destination.id:"final"}`).join('|');
  useEffect(()=>setSelectedLeg(null),[origin?.id,destination?.id,itinerary]);
  const selectLeg=index=>{setSelectedLeg(index);setMode('map');setView('navigate');};

  useEffect(()=>{
    setWalks([]);setWalkWarning('');
    if(!journey)return;
    if(journey.walks){setWalks(journey.walks);return;}
    const abort=new AbortController();
    const requests=[];
    if(origin?.addressCoordinates)requests.push({origin:origin.id,destination:origin.id,from_lat:origin.addressCoordinates.lat,from_lon:origin.addressCoordinates.lon});
    if(destination?.addressCoordinates)requests.push({origin:destination.id,destination:destination.id,to_lat:destination.addressCoordinates.lat,to_lon:destination.addressCoordinates.lon});
    (async()=>{for(let i=0;i<requests.length;i++){
      if(i)await new Promise(resolve=>setTimeout(resolve,1100));
      if(abort.signal.aborted)return;
      try{const result=await api('sptrans/walk',requests[i],abort.signal);
        if(!abort.signal.aborted){if(result.available)setWalks(paths=>[...paths,{...result,accessType:requests[i].from_lat!=null?'boarding':'destination'}]);else setWalkWarning(result.message);}
      }catch(e){if(!abort.signal.aborted)setWalkWarning(e.message);}
    }})();
    return()=>abort.abort();
  },[journey,origin,destination]);
  const qrRequest=useRef(),selectionRequest=useRef();
  useEffect(()=>()=>selectionRequest.current?.abort(),[]);
  useEffect(()=>{
    try{if(!save(sessionStorage,sessionKey,session))setNotice('Não foi possível salvar a sessão neste navegador.');}
    catch{setNotice('Armazenamento da sessão indisponível.');}
  },[session]);
  useEffect(()=>{
    const id=new URLSearchParams(location.search).get('stop');if(!id)return;
    // Uma URL mantida pela aplicação não é uma nova leitura de QR. Preserve o
    // ponto de embarque restaurado, incluindo coordenadas escolhidas manualmente.
    if(id===session.origin?.id){setCenter({lat:session.origin.lat,lon:session.origin.lon});return;}
    const abort=new AbortController();qrRequest.current=abort;
    api('sptrans/stops',{id},abort.signal).then(data=>{
      if(abort.signal.aborted)return;
      const stop=data.stops[0];setSession(s=>({...s,origin:stop}));setCenter({lat:stop.lat,lon:stop.lon});setMode('board');
    }).catch(e=>{if(!abort.signal.aborted)setNotice(e.message);});
    return()=>abort.abort();
  },[]);
  useEffect(()=>{
    if(!passengerPosition||origin||manualOrigin||new URLSearchParams(location.search).has('stop'))return;
    setSession(s=>({...s,origin:locationOrigin(passengerPosition)}));
    setMode('destination');setSearchRole('destination');
  },[passengerPosition,origin,manualOrigin]);
  const changeDestination=()=>{setPreserveViewport(true);setSelectedLeg(null);setJourney(null);setMode('destination');setView(favorites.length?'favorites':'navigate');};
  const changeOrigin=()=>{
    selectionRequest.current?.abort();
    setStreetView(null);setSelectedLeg(null);
    setPreserveViewport(true);
    setManualOrigin(true);setMode('origin');setSearchRole('origin');setJourney(null);setDestinationSearch(false);setView('navigate');
    setNotice('Selecione outro embarque no mapa, na busca ou nos favoritos.');
  };
  const requireBoarding=()=>{
    window.alert('Selecione o local de embarque antes de escolher o destino. Sua localização não está disponível.');
    setHighlightStopsRequest(value=>value+1);
    changeOrigin();
  };
  const togglePoint=role=>{
    const point=role==='origin'?(origin?.useLocation?null:origin):destination;
    if(!point&&role==='destination'&&!origin&&!passengerPosition){requireBoarding();return;}
    if(point&&!window.confirm(`Desmarcar ${role==='origin'?'o local de embarque':'o destino'} "${point.name}"? O outro local será mantido.`))return;
    selectionRequest.current?.abort();qrRequest.current?.abort();
    setPreserveViewport(true);setManualOrigin(true);setSelectedLeg(null);
    setJourney(null);setWalks([]);setWalkWarning('');setPlanningStatus('');
    setWatchedBus(null);setWatchedLines([]);setStreetView(null);setDestinationSearch(false);
    if(!point&&role==='destination'&&!origin&&passengerPosition){
      setManualOrigin(false);
      setSession(previous=>({...previous,origin:locationOrigin(passengerPosition),...(point?{destination:null}:{})}));
    }else if(point)setSession(previous=>({...previous,[role]:null}));
    if(role==='origin')history.replaceState(null,'',withLocationParams('/',location.search));
    setMode(role);setSearchRole(role);setView('navigate');setNotice('');
  };
  const useCurrentOrigin=()=>{
    selectionRequest.current?.abort();
    if(!passengerPosition)return;
    setManualOrigin(false);setSession(s=>({...s,origin:locationOrigin(passengerPosition)}));
    setJourney(null);setMode(destination?'board':'destination');setNotice('');
    history.replaceState(null,'',withLocationParams('/',location.search));
  };
  const onArea=point=>{setCenter({lat:point.lat,lon:point.lon});setViewport(previous=>previous&&Object.keys(point).every(key=>previous[key]===point[key])?previous:point);};
  const selectStop=async(stop,role)=>{
    if(role==='destination'&&!origin&&!passengerPosition){requireBoarding();return;}
    setPreserveViewport(false);
    selectionRequest.current?.abort();
    const abort=new AbortController();selectionRequest.current=abort;
    const boarding=origin||(passengerPosition?locationOrigin(passengerPosition):null);
    setNotice('');
    setStreetView(null);qrRequest.current?.abort();setJourney(null);setView('navigate');
    if(role==='origin'){
      setManualOrigin(true);setSession(s=>({...s,origin:{...stop,manualBoarding:true}}));
      history.replaceState(null,'',withLocationParams('/?stop='+encodeURIComponent(stop.id),location.search));
    }else {setSession(s=>({...s,origin:boarding,destination:stop}));history.replaceState(null,'',withLocationParams(boarding.useLocation?'/':'/?stop='+encodeURIComponent(boarding.id),location.search));}
    setDestinationSearch(false);setSelectedLeg(null);
    if(role==='origin'){
      setMode('destination');setSearchRole('destination');
    }else{
      setMode('board');setBoardRequest(value=>value+1);
    }
  };
  const selectFavorite=(stop,role)=>{
    selectionRequest.current?.abort();qrRequest.current?.abort();
    setSelectedLeg(null);setWatchedBus(null);setWatchedLines([]);setWalks([]);setPlanningStatus('');
    if(role==='destination'&&!origin&&!passengerPosition){
      setSession(previous=>({...previous,destination:stop}));setManualOrigin(true);
      setJourney(null);setMode('origin');setSearchRole('origin');setView('navigate');setNotice('Selecione o local de embarque.');return;
    }
    selectStop(stop,role);
  };
  const useCurrentLocation=async role=>{
    if(!passengerPosition)return;
    if(role==='origin'){setView('navigate');useCurrentOrigin();return;}
    selectionRequest.current?.abort();
    const abort=new AbortController();selectionRequest.current=abort;
    try{
      const point={lat:passengerPosition.lat,lon:passengerPosition.lon};
      const result=await api('sptrans/destination',point,abort.signal);
      if(abort.signal.aborted)return;
      if(!result.stop){setNotice(result.message||'Não há paradas próximas da sua localização.');return;}
      selectFavorite({...result.stop,name:'Minha localização',useLocation:true,addressCoordinates:point,destinationAddress:'Minha localização'},'destination');
    }catch(error){if(!abort.signal.aborted)setNotice(error.message);}
  };
  const selectMapPoint=async point=>{
    const role=mode==='origin'||!origin?'origin':'destination';
    selectionRequest.current?.abort();
    const abort=new AbortController();selectionRequest.current=abort;
    setNotice(role==='origin'?'Localizando embarque…':'Localizando destino…');
    try{
      const data=await api('sptrans/destination',point,abort.signal);
      if(abort.signal.aborted)return;
      if(!data.stop){setNotice(data.message||'Não há paradas próximas deste local.');return;}
      setSelectedLeg(null);setMapFocus(value=>value+1);
      await selectStop({...data.stop,name:'Local selecionado no mapa',
        destinationAddress:'Local selecionado no mapa',
        addressCoordinates:point,addressDistance:data.distance_meters},role);
    }catch(error){if(!abort.signal.aborted)setNotice(error.message);}
  };
  const choose=stop=>{if(routeSelected){openBoard();return;}selectStop(stop,!origin||mode==='origin'?'origin':'destination');};
  const cancelTrip=()=>{
    setManualOrigin(true);
    setWatchedBus(null);setWatchedLines([]);
    setPreserveViewport(true);
    setPassengerFocus(null);
    setSelectedLeg(null);setPlanningStatus('');setWalks([]);setWalkWarning('');
    setCancelRequested(false);
    selectionRequest.current?.abort();qrRequest.current?.abort();
    setStreetView(null);setSession({origin:null,destination:null});setJourney(null);
    setMode('origin');setSearchRole('origin');
    setDestinationSearch(false);setView('navigate');setNotice('');
    history.replaceState(null,'',withLocationParams('/',location.search));
  };
  const updateFavorites=next=>{
    setFavorites(next);try{if(!save(localStorage,favoritesKey,next))setNotice('Não foi possível salvar os favoritos neste navegador.');}catch{setNotice('Armazenamento de favoritos indisponível.');}
  };
  const favoritePoint=destination||origin;
  const favorite=()=>{
    if(!favoritePoint||favoritePoint.useLocation)return;
    const saved=favorites.find(s=>s.id===favoritePoint.id);
    if(saved)setRemovingFavorite(saved);else setEditingFavorite(favoritePoint);
  };
  const removeFavorite=()=>{
    if(!removingFavorite)return;
    updateFavorites(favorites.filter(s=>s.id!==removingFavorite.id));
    setRemovingFavorite(null);
  };
  const saveFavorite=name=>{
    const updated=favoriteStop({...editingFavorite,favoriteLabel:name});
    if(!updated)return;
    updateFavorites(favorites.some(s=>s.id===updated.id)?favorites.map(s=>s.id===updated.id?updated:s):[...favorites,updated].slice(-50));
    setEditingFavorite(null);
  };
  const openSearch=()=>{setSearchRole(origin&&mode!=='origin'?'destination':'origin');setDestinationSearch(true);};
  const stage=mode==='watch'?'Acompanhar ônibus':routeSelected?'Rota selecionada':mode==='destination'?'Selecionar destino':mode==='board'?(destination?'Ônibus da rota':'Próximos ônibus'):'Selecionar embarque';
  return <main className="passenger-shell sp-shell">
    <header className="passenger-header sp-header">
      <button type="button" className="sp-header-brand sp-about-button" aria-label={view==='more'?'Fechar Saiba mais pelo logo':'Saiba mais sobre o Ponto a Ponto'} aria-expanded={view==='more'} title={view==='more'?'Voltar ao mapa':'Saiba mais'} onClick={()=>setView(current=>current==='more'?'navigate':'more')}><span className="brand-mark app-brand-mark"><img src={appIcon} alt=""/></span></button>
      {view==='navigate'&&<section className="sp-navigation-state" aria-label="Estado da navegação"><div className="sp-state-heading"><strong role="status">{stage}</strong>
      </div></section>}
      <div className="sp-header-tools"><button className="icon-button" data-private aria-label="Configurações" title="Participação na pesquisa" onClick={()=>window.dispatchEvent(new Event('pap-open-research'))}><Icon name="settings"/></button><FullscreenButton onError={setNotice}/><button className="icon-button" aria-label="Buscar endereço" onClick={openSearch}><Icon name="search"/></button>
        <button className="icon-button" aria-label={resolvedTheme==='dark'?'Ativar modo claro':'Ativar modo escuro'} onClick={()=>setTheme(resolvedTheme==='dark'?'light':'dark')}><Icon name={resolvedTheme==='dark'?'sun':'moon'}/></button></div>
    </header>
    {locationError&&<div role="status" className="passenger-notice">{locationError}</div>}
    {notice&&<div role="status" className="passenger-notice">{notice}<button onClick={()=>setNotice('')} aria-label="Fechar aviso">×</button></div>}
    {view!=='more'&&<div className="sp-navigation"><section className="sp-map-panel">
      <SaoPauloMap itineraries={mode==='watch'?(watchedLines.length?lineItineraries:liveBus?.itinerary?[{...liveBus.itinerary,trip_id:watchedBus?.trip_id,code:watchedBus?.code}]:[]):[]} highlightStopsRequest={highlightStopsRequest} coordinateFocus={coordinateFocus} selectingPoint={selectingPoint} preserveViewport={preserveViewport} confirmDestination={mode==='watch'} approaches={[...lineApproaches,...(liveBus?.passedApproaches||[])]} approachFocusKey={mode==='watch'?(watchedLines.length?watchedLines.map(l=>l.trip_id).join(':'):watchedBus?.trip_id+':'+watchedBus?.vehicle):null} approach={liveBus?.approach} passengerFocus={passengerFocus} passengerPosition={passengerPosition} focusKey={`${origin?.id}:${destination?.id}:${mapFocus}:${selectedLeg}`} routeSelected={routeSelected} stops={selectingPoint?(streetView?streetView.stops:stops):[]} focusStops={streetView?.stops} origin={leg?.origin||journey?.legs[0]?.origin||(origin?.useLocation?null:origin)} destination={destination?.addressCoordinates?{...destination,...destination.addressCoordinates}:destination} journey={shownJourney} fullJourney={journey} walks={shownWalks} center={center} onStop={choose} onArea={onArea} onMapPoint={selectMapPoint}/>
      {mode!=='board'&&<div className="sp-map-point-controls" data-has-light={selectingPoint} aria-label="Escolher embarque e destino"><PointControl kind="origin" point={origin} selecting={mode==='origin'} onClick={()=>togglePoint('origin')}/><PointControl kind="destination" point={destination} selecting={mode==='destination'} onClick={()=>togglePoint('destination')}/></div>}
      {selectingPoint&&streetView&&<div className="sp-schematic-note">{streetView.label} · {streetView.stops.length} {streetView.match_method==='nearby'?'paradas próximas (até 400 m)':'paradas cadastradas'}{streetView.match_method==='nearby'&&<small> · Podem incluir ruas vizinhas.</small>} <button onClick={()=>setStreetView(null)}>Mostrar todos os pontos</button></div>}
      {mode==='watch'&&watchedLines.length>0&&<div className="sp-watch-panel" role="status"><strong>{watchedLines.length} linhas acompanhadas</strong><span>Atualização a cada 5 s</span>{(lineTracking||watchedLines).map(l=><span key={l.trip_id}>{l.code}: {!lineTracking?'consultando…':l.approach?'veículo '+l.approach.vehicle.id:l.itinerary?.geometry?.length?'trajeto disponível · sem posição de ônibus disponível':'posição e trajeto indisponíveis'}</span>)}</div>}
      {mode==='watch'&&watchedBus&&<div className="sp-watch-panel" role="status"><strong>{watchedBus.code} · veículo {watchedBus.vehicle}</strong><span>{!liveBus?'Consultando posição…':liveBus.approach?'Percurso até '+origin.name+' · próximo veículo '+liveBus.approach.vehicle.id+' · atualização a cada 5 s':liveBus.passedApproaches?.length?'Ônibus após o embarque · até 500 m · atualização a cada 5 s':liveBus.itinerary?.geometry?.length?'Posição indisponível no momento · trajeto da linha disponível no mapa':'Posição ou percurso até este ponto indisponível no momento.'}</span></div>}
      {routeSelected&&planningStatus&&<div className="sp-map-status" role="status">{planningStatus}</div>}
      {((origin&&!origin.useLocation)||destination)&&<div className="sp-schematic-note sp-route-legend">{origin&&(!origin.useLocation||destination)?<button className="icon-button" aria-label="Horários de embarque" title="Horários de embarque" onClick={openBoard}><Icon name="list"/></button>:null}{mode==='watch'&&(lineItineraries.length>0||liveBus?.itinerary)&&<div className="sp-itinerary-legend" role="note"><span>Antes do embarque</span><span>Após o embarque</span><small>Setas: sentido · separação visual de ida e volta</small><small>I: início do traçado da linha</small>{[...lineItineraries,...(watchedBus&&liveBus?.itinerary?[liveBus.itinerary]:[])].some(i=>i.terminal_mismatch)?<small>Bandeira: fim do traçado GTFS. Última parada cadastrada divergente; desembarque final não confirmado.</small>:<small>Bandeira: último ponto da linha</small>}{[...lineItineraries,...(watchedBus&&liveBus?.itinerary?[liveBus.itinerary]:[])].some(i=>!i.split_available)&&<small>Divisão no embarque indisponível para um dos trajetos.</small>}</div>}{journey&&<><div className="sp-route-controls">{journey.legs.length>1&&<label>Trecho <select aria-label="Trecho exibido no mapa" value={leg?selectedLeg:'all'} onChange={e=>setSelectedLeg(e.target.value==='all'?null:Number(e.target.value))}><option value="all">Viagem completa</option>{journey.legs.map((l,i)=><option key={i} value={i}>{String.fromCharCode(65+i)} → {i===journey.legs.length-1?'Destino':String.fromCharCode(66+i)} · {l.code} · {l.headsign}</option>)}</select></label>}<div className="sp-route-keys"><span>Ônibus</span><span className="sp-walk-key">A pé</span></div></div>{journey.legs.some(l=>!l.geometry?.length)&&<small>Traçado GTFS indisponível em um trecho.</small>}{walkWarning&&<small>{walkWarning}</small>}</>}<button className="icon-button sp-map-cancel" aria-label="Cancelar viagem" title="Cancelar viagem" onClick={()=>setCancelRequested(true)}><Icon name="close"/></button></div>}
      {selectingPoint&&(searching||searchError)&&<div className="sp-map-status" role={searchError?'alert':'status'}>{searchError||'Atualizando pontos…'}</div>}
    </section></div>}
    <FavoritesDialog open={view==='favorites'&&!previewStop} favorites={favorites} onClose={()=>setView('navigate')} onSelect={selectFavorite} onPreview={setPreviewStop} onEdit={setEditingFavorite} onRemove={setRemovingFavorite} onLocation={useCurrentLocation} hasLocation={!!passengerPosition}/>
    <BoardDialog open={!!previewStop} active={!!previewStop} origin={previewStop} destination={null} onClose={()=>setPreviewStop(null)} onCancel={()=>setPreviewStop(null)} onFavorite={()=>setEditingFavorite(previewStop)} isFavorite={true} onDestination={()=>{const stop=previewStop;setPreviewStop(null);selectFavorite(stop,'destination');}} onJourney={ignorePreviewJourney} onStatus={ignorePreviewJourney} onWatchBus={bus=>{setSession(s=>({...s,origin:previewStop,destination:null}));setPreviewStop(null);setView('navigate');setWatchedBus(bus);setMode('watch');}} onWatchLines={lines=>{setSession(s=>({...s,origin:previewStop,destination:null}));setPreviewStop(null);setView('navigate');setWatchedLines(lines);setMode('watch');}}/>
    {view==='more'&&<section className="passenger-screen screen-content more-screen sp-more">
      <div className="sp-more-heading"><h2>Saiba mais</h2><button type="button" className="icon-button" aria-label="Fechar Saiba mais" title="Voltar ao mapa" onClick={()=>setView('navigate')}><Icon name="close"/></button></div>
      <p>O Ponto a Ponto (PaP) é um protótipo acadêmico do Projeto Integrador da UNIVESP. A aplicação ajuda a planejar viagens de ônibus em São Paulo a partir do ponto de embarque e do destino, sem exigir que o passageiro conheça previamente os números das linhas.</p>
      <h3>Escolha a origem e o destino</h3>
      <p>Ao abrir o QR Code de uma parada, o PaP identifica o embarque e abre a lista de próximos ônibus. Você pode acompanhar uma linha ou escolher um destino para planejar a viagem.</p>
      <p>O botão com o ônibus representa o local de embarque; a bandeira quadriculada representa o destino. Borda pontilhada e transparência indicam que o local ainda não foi definido. Ao selecionar um local, o botão fica com borda sólida e uma marca de confirmação. O destaque de seleção indica qual local você está escolhendo no mapa.</p>
      <p>Toque no botão do local que deseja escolher e selecione um ponto no mapa, busque um endereço pela lupa ou use um favorito. O destino também pode ser uma posição do mapa, escolhida com um toque longo sem arrastar. Para trocar um local já definido, toque em seu botão e confirme que deseja desmarcá-lo; o outro local será mantido.</p>
      <p>Com a localização disponível, você pode escolher o destino sem fixar uma parada de embarque: o PaP considera a caminhada até pontos próximos. A localização do passageiro não aparece no botão como uma parada escolhida. Sem localização e sem embarque, um aviso solicita a escolha da origem e abre esse modo de seleção.</p>
      <p>Para locais definidos por coordenadas, a busca considera até três paradas próximas em cada extremo e compara as combinações viáveis pelo tempo total. Uma parada escolhida diretamente permanece como referência fixa.</p>
      <h3>Controles do mapa</h3>
      <p>Use + e − para aproximar ou afastar o mapa e o botão de localização para centralizar sua posição. Ao escolher embarque ou destino, a lâmpada permite atenuar os pontos e reduzir a poluição visual. Apagada, ela fica pontilhada e transparente; toque novamente para destacar os pontos.</p>
      <p>Alterar ou desmarcar os locais mantém o enquadramento do mapa. O botão com a lista, na parte inferior, abre os próximos ônibus ou as alternativas da viagem. O botão de mapa dentro dessa janela permite voltar ao acompanhamento.</p>
      <h3>Próximos ônibus</h3>
      <p>Ordene a lista por próximos ônibus, nome do destino ou número da linha. Quando disponível, “Embarque em” informa o tempo até a chegada prevista, acompanhado do horário, veículo e indicação de acessibilidade. Sem previsão operacional, são exibidos os horários ou frequências programados.</p>
      <p>Toque em “Ver ônibus no mapa” para acompanhar um veículo específico. Toque em outra área do cartão da linha para acompanhar os próximos veículos disponíveis dessa linha. Para selecionar várias linhas, mantenha um cartão pressionado sem arrastar; depois marque as demais com toques simples e volte ao mapa.</p>
      <p>O percurso de aproximação aparece em roxo. Ônibus que já passaram pelo embarque continuam visíveis por até 500 m ao longo do trajeto, com transparência. As posições no acompanhamento são consultadas a cada 5 segundos; a lista de próximos ônibus é atualizada a cada 30 segundos. A disponibilidade depende dos dados retornados pela SPTrans.</p>
      <h3>Compare as alternativas</h3>
      <p>Escolha a ordenação por trajeto mais rápido, menos baldeações ou menos caminhada. Cada alternativa informa as linhas, baldeações, caminhada e tempos disponíveis. Toque no cartão para visualizar o percurso. Uma alternativa somente a pé também pode aparecer quando houver um caminho verificado.</p>
      <p>As linhas azuis representam ônibus e as linhas rosas tracejadas representam caminhada. Quando a viagem possui baldeações, o seletor “Trecho” permite examinar cada parte ou a viagem completa.</p>
      <p>O tempo indicado “no planejamento” corresponde à busca realizada. Quando há previsão operacional compatível, o embarque é atualizado e a chegada de uma viagem com um único ônibus pode ser estimada novamente. Em viagens com baldeações, siga a indicação de reiniciar a busca para atualizar as conexões. Uma previsão de embarque não garante a transferência seguinte.</p>
      <h3>Favoritos e cancelamento</h3>
      <p>“Salvar ponto” guarda uma referência ao local, que pode receber um nome como Casa ou Trabalho e ser reutilizada como embarque ou destino. Os favoritos ficam neste navegador e não representam viagens salvas.</p>
      <p>Ao confirmar o cancelamento da viagem pelo botão ×, o trajeto, o embarque e o destino são removidos. Os favoritos e o enquadramento do mapa são preservados. Na lista sem destino, o × solicita a confirmação para desmarcar o embarque.</p>
      <h3>Dados e limites do protótipo</h3>
      <p>O GTFS da SPTrans fornece o cadastro de paradas, linhas, trajetos e programação do serviço. O Olho Vivo fornece posições e previsões operacionais quando disponíveis. A ausência de previsão não significa que a linha deixou de circular. Horários e frequências programados não indicam a posição atual do veículo.</p>
      <p>A busca tem limites de tempo, candidatos e verificações; não garante encontrar a melhor rota de toda a rede. A pequena águia identifica alternativas calculadas pelo RAPTOR, usado como busca alternativa quando as conexões preparadas não retornam uma opção viável. O planejamento admite até duas baldeações.</p>
      <p>As caminhadas de acesso, saída e transferência são verificadas pelo serviço de rotas a pé, com limite de 1 km por ligação e velocidade de referência de 4,5 km/h. Uma alternativa somente a pé pode ter distância maior. Caminhadas que não puderem ser verificadas não são apresentadas como percursos confirmados.</p>
      <p>O planejamento não é refeito a cada atualização da posição dos ônibus. Use “Reiniciar busca” para consultar novamente. Os resultados dependem da versão dos dados e da disponibilidade dos serviços. Integrações tarifárias não são calculadas; confira a sinalização e as condições de operação no local.</p>
      <p>O PaP é um projeto acadêmico independente, não um aplicativo oficial da SPTrans. O uso dos dados públicos não representa parceria ou validação institucional.</p>
      <a href="https://www.sptrans.com.br/desenvolvedores/" target="_blank" rel="noreferrer">Dados e recursos para desenvolvedores da SPTrans</a>
    </section>}

    <BoardDialog onWatchLines={lines=>{setWatchedBus(null);setWatchedLines(lines);setMode(lines.length?'watch':origin?'destination':'origin');setView('navigate');}} onWatchBus={bus=>{setWatchedLines([]);setWatchedBus(bus);setMode('watch');setView('navigate');setDestinationSearch(false);}} boardingLive={liveBus} passengerPosition={passengerPosition} onChooseJourney={()=>setMapFocus(value=>value+1)} requestId={boardRequest} active={!!origin&&mode!=='destination'&&mode!=='origin'&&(!origin.useLocation||!!destination)} onStatus={setPlanningStatus} open={view==='navigate'&&mode==='board'&&!destinationSearch} origin={origin} destination={destination} onClose={()=>{setSelectedLeg(null);setMode(destination?'map':origin?'destination':'origin');}} onDestination={()=>togglePoint('destination')} onCancel={()=>setCancelRequested(true)} onFavorite={favorite} isFavorite={favorites.some(s=>s.id===favoritePoint?.id)} onJourney={setJourney}/>
    <DestinationSearch onCoordinates={point=>{setPreserveViewport(true);setStreetView(null);setView('navigate');setMode(previous=>previous==='board'?'map':previous);setCoordinateFocus({...point});}} origin={origin?.useLocation?null:origin} onStreet={data=>{setPreserveViewport(false);setStreetView(data);setJourney(null);setView('navigate');setMode(searchRole);}} open={destinationSearch} role={searchRole} onClose={()=>setDestinationSearch(false)} onSelect={stop=>selectStop(stop,searchRole)}/>
    <CancelTripDialog boardingOnly={!destination} open={cancelRequested} onConfirm={cancelTrip} onClose={()=>setCancelRequested(false)}/>
    <RemoveFavoriteDialog stop={removingFavorite} onConfirm={removeFavorite} onClose={()=>setRemovingFavorite(null)}/>
    <FavoriteNameDialog stop={editingFavorite} onSave={saveFavorite} onClose={()=>setEditingFavorite(null)}/>
    <nav className="bottom-nav" aria-label="Navegação principal">{[['navigate','map','Navegação'],['favorites','star','Favoritos'],['feedback','feedback','Feedback']].map(([id,icon,label])=><button key={id} className={view===id?'active':''} aria-current={view===id?'page':undefined} onClick={()=>id==='feedback'?window.dispatchEvent(new Event('pap-open-feedback')):setView(id)}><Icon name={icon}/><span>{label}</span></button>)}</nav>
  </main>;
}
