import {useEffect,useState,useRef,useMemo} from 'react';
import {api} from './api.js';
import {useMapStops} from './useMapStops.js';
import {useTheme} from './useTheme.js';
import {readSession,readFavorites,save,sessionKey,favoritesKey} from './spSession.js';
import SaoPauloMap from './SaoPauloMap.jsx';
import Icon from './Icon.jsx';
import DestinationSearch from './DestinationSearch.jsx';
import BoardDialog from './BoardDialog.jsx';
import FavoriteNameDialog from './FavoriteNameDialog.jsx';
import RemoveFavoriteDialog from './RemoveFavoriteDialog.jsx';
import CancelTripDialog from './CancelTripDialog.jsx';
import './sao-paulo.css';
function initialSession(){try{return readSession(sessionStorage);}catch{return {origin:null,destination:null};}}
function initialFavorites(){try{return readFavorites(localStorage);}catch{return [];}}
export default function SaoPaulo(){
  const {resolvedTheme,setTheme}=useTheme();
  const [session,setSession]=useState(initialSession),[favorites,setFavorites]=useState(initialFavorites);
  const [editingFavorite,setEditingFavorite]=useState(null),[removingFavorite,setRemovingFavorite]=useState(null);
  const [boardRequest,setBoardRequest]=useState(0);
  const [cancelRequested,setCancelRequested]=useState(false);
  const openBoard=()=>{setDestinationSearch(false);setView('navigate');setMode('board');setBoardRequest(n=>n+1);};
  const [center,setCenter]=useState({lat:-23.5505,lon:-46.6333}),[viewport,setViewport]=useState(null);
  const [view,setView]=useState('navigate'),[mode,setMode]=useState('origin'),[notice,setNotice]=useState('');
  const [destinationSearch,setDestinationSearch]=useState(false),[searchRole,setSearchRole]=useState('origin'),[journey,setJourney]=useState(null);
  const [planningStatus,setPlanningStatus]=useState('');
  const routeSelected=!!session.origin&&!!session.destination&&mode!=='destination';
  const {stops,loading:searching,error:searchError}=useMapStops(routeSelected?null:viewport);
  const {origin,destination}=session;
  const [streetView,setStreetView]=useState(null);
  const [walks,setWalks]=useState([]),[walkWarning,setWalkWarning]=useState('');
  const [selectedLeg,setSelectedLeg]=useState(null);
  const leg=selectedLeg===null?null:journey?.legs[selectedLeg];
  const shownJourney=useMemo(()=>leg?{...journey,legs:[leg]}:journey,[journey,leg]);
  const shownWalks=useMemo(()=>!leg?walks:walks.filter(path=>(path.accessType==='boarding'&&selectedLeg===0)||(path.accessType==='destination'&&selectedLeg===journey.legs.length-1)||(path.accessType==='transfer'&&(path.before_leg===selectedLeg||path.before_leg===selectedLeg+1))),[leg,walks,selectedLeg,journey]);
  const itinerary=journey?.legs.map(l=>`${l.trip_id}:${l.origin.id}:${l.destination.id}`).join('|');
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
    const abort=new AbortController();qrRequest.current=abort;
    api('sptrans/stops',{id},abort.signal).then(data=>{
      if(abort.signal.aborted)return;
      const stop=data.stops[0];setSession(s=>({...s,origin:stop}));setCenter({lat:stop.lat,lon:stop.lon});setMode('board');
    }).catch(e=>{if(!abort.signal.aborted)setNotice(e.message);});
    return()=>abort.abort();
  },[]);
  const onArea=point=>{setCenter({lat:point.lat,lon:point.lon});setViewport(previous=>previous&&Object.keys(point).every(key=>previous[key]===point[key])?previous:point);};
  const selectStop=async(stop,role)=>{
    selectionRequest.current?.abort();
    const abort=new AbortController();selectionRequest.current=abort;
    const boarding=origin;
    setNotice('');
    setStreetView(null);qrRequest.current?.abort();setJourney(null);setView('navigate');
    if(role==='origin'){
      setSession(s=>({...s,origin:stop,destination:null}));
      history.replaceState(null,'','/sao-paulo/?stop='+encodeURIComponent(stop.id));
    }else {setSession(s=>({...s,origin:boarding,destination:stop}));history.replaceState(null,'','/sao-paulo/?stop='+encodeURIComponent(boarding.id));}
    setMode('board');
  };
  const choose=stop=>{if(routeSelected){openBoard();return;}selectStop(stop,mode==='destination'&&origin?'destination':'origin');};
  const cancelTrip=()=>{
    setCancelRequested(false);
    selectionRequest.current?.abort();
    setStreetView(null);qrRequest.current?.abort();setSession({origin:null,destination:null});setJourney(null);setMode('origin');setDestinationSearch(false);setView('navigate');setNotice('');
    history.replaceState(null,'','/sao-paulo/');
  };
  const updateFavorites=next=>{
    setFavorites(next);try{if(!save(localStorage,favoritesKey,next))setNotice('Não foi possível salvar os favoritos neste navegador.');}catch{setNotice('Armazenamento de favoritos indisponível.');}
  };
  const favorite=()=>{
    if(!origin)return;
    const saved=favorites.find(s=>s.id===origin.id);
    if(saved)setRemovingFavorite(saved);else setEditingFavorite(origin);
  };
  const removeFavorite=()=>{
    if(!removingFavorite)return;
    updateFavorites(favorites.filter(s=>s.id!==removingFavorite.id));
    setRemovingFavorite(null);
  };
  const saveFavorite=name=>{
    const updated={...editingFavorite,favoriteLabel:name};
    updateFavorites(favorites.some(s=>s.id===updated.id)?favorites.map(s=>s.id===updated.id?updated:s):[...favorites,updated].slice(-50));
    setEditingFavorite(null);
  };
  const openSearch=()=>{setSearchRole(origin&&mode!=='origin'?'destination':'origin');setDestinationSearch(true);};
  const stage=routeSelected?'Rota selecionada':mode==='destination'?'Selecionar destino':mode==='board'?(destination?'Ônibus da rota':'Próximos ônibus'):'Selecionar local de embarque';
  return <main className="passenger-shell sp-shell">
    <header className="passenger-header sp-header">
      <div className="sp-header-brand"><span className="brand-mark"><Icon name="bus"/></span><div><h1>Ponto a Ponto</h1><p>São Paulo · SPTrans</p></div></div>
      {view==='navigate'&&<section className="sp-navigation-state" aria-label="Estado da navegação"><div className="sp-state-heading"><strong role="status">{stage}</strong>
        {mode==='destination'?<button className="text-button" onClick={()=>{selectionRequest.current?.abort();setNotice('');setMode('board');}}>Cancelar seleção</button>:origin&&<button className="icon-button" aria-label="Ver próximos ônibus" title="Ver próximos ônibus" onClick={openBoard}><Icon name="list"/></button>}
        {origin&&<button className="icon-button" aria-label="Cancelar viagem" title="Cancelar viagem" onClick={()=>setCancelRequested(true)}><Icon name="close"/></button>}
      </div></section>}
      <div className="sp-header-tools"><button className="icon-button" aria-label="Buscar endereço" onClick={openSearch}><Icon name="search"/></button>
        <button className="icon-button" aria-label={resolvedTheme==='dark'?'Ativar modo claro':'Ativar modo escuro'} onClick={()=>setTheme(resolvedTheme==='dark'?'light':'dark')}><Icon name={resolvedTheme==='dark'?'sun':'moon'}/></button></div>
    </header>
    {notice&&<div role="status" className="passenger-notice">{notice}<button onClick={()=>setNotice('')} aria-label="Fechar aviso">×</button></div>}
    {view==='navigate'&&<div className="sp-navigation"><section className="sp-map-panel">
      <SaoPauloMap routeSelected={routeSelected} stops={streetView?streetView.stops:stops} focusStops={streetView?.stops} origin={leg?.origin||journey?.legs[0]?.origin||origin} destination={leg?.destination||journey?.legs.at(-1)?.destination||destination} journey={shownJourney} fullJourney={journey} walks={shownWalks} center={center} onStop={choose} onArea={onArea}/>
      {streetView&&<div className="sp-schematic-note">{streetView.label} · {streetView.stops.length} {streetView.match_method==='nearby'?'paradas próximas (até 400 m)':'paradas cadastradas'}{streetView.match_method==='nearby'&&<small> · Podem incluir ruas vizinhas.</small>} <button onClick={()=>setStreetView(null)}>Mostrar todos os pontos</button></div>}
      {routeSelected&&planningStatus&&<div className="sp-map-status" role="status">{planningStatus}</div>}
      {journey&&<div className="sp-schematic-note sp-route-legend"><button className="icon-button" aria-label="Horários de embarque" title="Horários de embarque" onClick={openBoard}><Icon name="list"/></button><label>Mostrar no mapa <select aria-label="Trecho exibido no mapa" value={leg?selectedLeg:'all'} onChange={e=>setSelectedLeg(e.target.value==='all'?null:Number(e.target.value))}><option value="all">Viagem completa</option>{journey.legs.map((l,i)=><option key={i} value={i}>{String.fromCharCode(65+i)} → {i===journey.legs.length-1?'Destino':String.fromCharCode(66+i)} · {l.code} · {l.headsign}</option>)}</select></label><span>Ônibus</span><span className="sp-walk-key">A pé</span>{journey.legs.some(l=>!l.geometry?.length)&&<small>Traçado GTFS indisponível em um trecho.</small>}{walkWarning&&<small>{walkWarning}</small>}</div>}
      {!routeSelected&&(searching||searchError)&&<div className="sp-map-status" role={searchError?'alert':'status'}>{searchError||'Atualizando pontos…'}</div>}
    </section></div>}
    {view==='favorites'&&<section className="passenger-screen screen-content sp-favorites"><h2>Pontos favoritos</h2>{mode==='destination'&&<div className="sp-board-actions"><button className="primary" onClick={()=>setView('navigate')}>Buscar no mapa</button><button className="text-button" onClick={()=>{selectionRequest.current?.abort();setNotice('');setMode('board');setView('navigate');}}>Cancelar seleção</button></div>}<p>{mode==='destination'?'Escolha o destino.':'Escolha o local de embarque.'}</p>{!favorites.length&&<p>Salve seu embarque na lista de próximos ônibus.</p>}{favorites.map(s=><div className="favorite-row" key={s.id}><button onClick={()=>choose(s)}><Icon name="star"/><span>{s.favoriteLabel||s.name}<small>{s.favoriteLabel?` · ${s.name}`:''} · {s.id}</small></span></button><button className="icon-button" title="Renomear favorito" aria-label={'Renomear favorito '+(s.favoriteLabel||s.name)} onClick={()=>setEditingFavorite(s)}><Icon name="edit"/></button><button className="icon-button" title="Remover favorito" aria-label={'Remover favorito '+(s.favoriteLabel||s.name)} onClick={()=>setRemovingFavorite(s)}><Icon name="trash"/></button></div>)}</section>}
    {view==='more'&&<section className="passenger-screen screen-content more-screen sp-more">
      <h2>Saiba mais</h2>
      <p>O Ponto a Ponto (PaP) é um protótipo acadêmico do Projeto Integrador da UNIVESP. A aplicação ajuda a planejar viagens de ônibus em São Paulo a partir do ponto de embarque e do destino, sem exigir que o passageiro conheça previamente os números das linhas.</p>
      <h3>O que foi desenvolvido com os dados da SPTrans</h3>
      <p>O cadastro disponibilizado pela SPTrans no formato GTFS reúne paradas, linhas, sequências de atendimento, trajetos e programação de horários. Esses dados permitem localizar os pontos no mapa, indicar os sentidos atendidos e identificar quais ônibus podem levar o passageiro ao destino.</p>
      <p>O planejamento considera a ordem das paradas, os dias de operação, os horários e intervalos programados. A viagem pode combinar até duas baldeações, inclusive com caminhada entre pontos próximos. O PaP compara alternativas de embarque e desembarque e apresenta as três rotas calculadas com menor tempo total de caminhada, espera e ônibus. A lista pode ser expandida para mostrar todas as alternativas calculadas.</p>
      <h3>Acompanhe cada etapa da viagem</h3>
      <p>O mapa mostra o trajeto dos ônibus a partir da geometria fornecida no GTFS. A origem recebe a letra A, as baldeações recebem B, C e assim por diante, e o destino final é indicado por uma estrela. É possível visualizar a viagem completa ou selecionar apenas um trecho, mantendo a identificação dos pontos.</p>
      <p>As linhas contínuas azuis representam os trechos de ônibus. Os percursos a pé disponíveis aparecem em rosa tracejado. A busca de endereços utiliza Photon e OpenStreetMap, e os caminhos de pedestres são consultados no serviço de rotas a pé FOSSGIS/OSRM. Esses recursos complementam o cadastro da SPTrans.</p>
      <h3>Horários programados e informações em tempo real</h3>
      <p>A integração com a API Olho Vivo foi desenvolvida para consultar previsões de chegada e posições de veículos. As previsões são apresentadas quando o serviço está disponível e a linha e a parada podem ser identificadas com segurança. A lista de ônibus é atualizada periodicamente enquanto está aberta.</p>
      <p>Quando não há informações em tempo real, o PaP apresenta estimativas baseadas nos horários e intervalos programados. Esses valores não indicam a posição atual do ônibus e podem variar com o trânsito e a operação. A falta de uma previsão não significa que a linha deixou de circular, e o horário de uma baldeação não garante a conexão.</p>
      <h3>Busca, favoritos e acesso por QR Code</h3>
      <p>Ao buscar uma rua sem número, o mapa exibe suas paradas identificadas no cadastro. Se o nome não for encontrado, a busca pode mostrar pontos próximos ao local selecionado, com essa condição indicada na tela. Com um endereço completo, a aplicação sugere uma parada próxima e verifica o sentido da viagem.</p>
      <p>Os pontos favoritos podem receber nomes como Casa, Trabalho ou Faculdade e ser usados na escolha do destino. Eles ficam salvos neste navegador. O QR Code de uma parada abre a aplicação com o embarque identificado, facilitando o início da consulta pelo celular.</p>
      <h3>Limites do protótipo</h3>
      <p>O planejamento depende da versão do cadastro importado e da disponibilidade dos serviços consultados. Paradas, trajetos e horários podem mudar. As alternativas consideram caminhadas de até 200 m no embarque, no desembarque e nas baldeações, a 4 km/h. Os percursos a pé precisam estar disponíveis no serviço de rotas. Integrações tarifárias não são calculadas. Confira a sinalização no local e as informações da operação antes de embarcar.</p>
      <p>O PaP é um projeto acadêmico independente, não um aplicativo oficial da SPTrans. O uso dos dados públicos não representa parceria ou validação institucional.</p>
      <a href="https://www.sptrans.com.br/desenvolvedores/" target="_blank" rel="noreferrer">Dados e recursos para desenvolvedores da SPTrans</a>
    </section>}

    <BoardDialog requestId={boardRequest} active={!!origin&&mode!=='destination'} onStatus={setPlanningStatus} open={view==='navigate'&&mode==='board'&&!destinationSearch} origin={origin} destination={destination} onSelectLeg={selectLeg} onClose={()=>{setSelectedLeg(null);setMode(destination?'map':'origin');}} onDestination={()=>{setJourney(null);setMode('destination');setView(favorites.length?'favorites':'navigate');}} onCancel={()=>setCancelRequested(true)} onFavorite={favorite} isFavorite={favorites.some(s=>s.id===origin?.id)} onJourney={setJourney}/>
    <DestinationSearch origin={origin} onStreet={data=>{setStreetView(data);setJourney(null);setView('navigate');setMode(searchRole);}} open={destinationSearch} role={searchRole} onClose={()=>setDestinationSearch(false)} onSelect={stop=>selectStop(stop,searchRole)}/>
    <CancelTripDialog open={cancelRequested} onConfirm={cancelTrip} onClose={()=>setCancelRequested(false)}/>
    <RemoveFavoriteDialog stop={removingFavorite} onConfirm={removeFavorite} onClose={()=>setRemovingFavorite(null)}/>
    <FavoriteNameDialog stop={editingFavorite} onSave={saveFavorite} onClose={()=>setEditingFavorite(null)}/>
    <nav className="bottom-nav" aria-label="Navegação principal">{[['navigate','map','Navegação'],['favorites','star','Favoritos'],['more','info','Saiba mais']].map(([id,icon,label])=><button key={id} className={view===id?'active':''} aria-current={view===id?'page':undefined} onClick={()=>setView(id)}><Icon name={icon}/><span>{label}</span></button>)}</nav>
  </main>;
}
