import {directedPath} from './routeDirection.js';
import {isRail,railLabel,railColor,railDash,stationSymbol} from './railStyle.js';
import {drawRailNetwork} from './railNetworkLayer.js';
import {trace} from './usability.js';
import {developmentTools} from './environment.js';
import destinationPointIcon from './assets/destination-point.png';
import boardingPointIcon from './assets/boarding-point.png';
import { useEffect, useRef, useMemo, useState } from 'react';
import L from 'leaflet';
import Icon from './Icon.jsx';
import {StopCanvas} from './StopCanvas.js';
import StopTransparencyControl from './StopTransparencyControl.jsx';
import {bindMapLongPress} from './mapLongPress.js';
import {api} from './api.js';
const EMPTY_LIST=Object.freeze([]);
function drawRouteStops(group,routes,excluded=[]){
  const hidden=new Set(excluded.filter(Boolean).map(stop=>stop.id));
  const points=new Map();
  for(const route of routes)for(const [index,stop] of (route.stops||[]).entries()){
    if(hidden.has(stop.id)||!Number.isFinite(stop.lat)||!Number.isFinite(stop.lon))continue;
    const key=JSON.stringify([stop.id,stop.lat,stop.lon]);
    const past=route.split_available&&Number.isInteger(route.boarding_index)&&index<route.boarding_index;
    const record=points.get(key)||{stop,past,labels:new Set(),color:isRail(route)?railColor(route):null,railway:isRail(route)||isRail(stop)};
    record.past=record.past&&past;
    record.labels.add(isRail(route)?railLabel(route):route.code?`Linha ${route.code}`:'Parada da rota');
    points.set(key,record);
  }
  for(const {stop,past,labels,color,railway} of points.values()){
    const name=`${stop.name||stop.id} · ${[...labels].join(' · ')}`;
    const content=document.createElement('span');content.textContent=name;
    L.marker([stop.lat,stop.lon],{pane:'routeStops',title:name,alt:name,
      icon:L.divIcon({className:'sp-route-stop'+(past?' sp-route-stop-before':'')+(railway?' sp-route-station':''),html:`<span aria-hidden="true"${color?` style="border-color:${color}"`:''}></span>`,iconSize:[24,24],iconAnchor:[12,12]})})
      .bindTooltip(()=>{const label=document.createElement('span');label.textContent=name;return label;})
      .bindPopup(content).addTo(group);
  }
}
export default function SaoPauloMap({ itineraries=EMPTY_LIST, highlightStopsRequest=0, selectingPoint=false, preserveViewport=false, confirmDestination=false, approaches=[], approachFocusKey, approach, passengerFocus, coordinateFocus, passengerPosition, stops, routeSelected=false, focusStops, focusKey, origin, destination, detail, journey, fullJourney, walking, walks=EMPTY_LIST, center, onStop, onArea, onMapPoint, mapPointRole='destination', onFavoritePoint, isFavoritePoint }) {
  const [dimmerActive,setDimmerActive]=useState(false);
  const [transparentStops,setTransparentStops]=useState(false);
  useEffect(()=>{setTransparentStops(false);},[highlightStopsRequest]);
  const [stopTransparency,setStopTransparency]=useState(()=>{
    try { const stored=localStorage.getItem('pap-stop-transparency'); const value=Number(stored); return stored!==null&&Number.isFinite(value)&&value>=0&&value<=100?value:75; } catch { return 75; }
  });
  const changeTransparency=value=>{
    setStopTransparency(value);setTransparentStops(true);
    try { localStorage.setItem('pap-stop-transparency',String(value)); } catch { /* Storage may be unavailable. */ }
  };
  const commitTransparency=value=>{
    if(value===0){
      // Fully opaque means lamp on; retain the default 25% opacity for lamp off.
      changeTransparency(75);
      setTransparentStops(false);
    }else changeTransparency(value);
  };
  const host=useRef(), map=useRef(), click=useRef(onStop), area=useRef(onArea);
  const locationButton=useRef(null), mapPoint=useRef(onMapPoint);
  const confirmPoint=useRef(confirmDestination), destinationPopup=useRef(null);
  confirmPoint.current=confirmDestination;
  mapPoint.current=onMapPoint;
  const favoritePoint=useRef(),favoriteCheck=useRef(),pointRole=useRef();
  favoritePoint.current=onFavoritePoint;favoriteCheck.current=isFavoritePoint;pointRole.current=mapPointRole;
  useEffect(()=>{destinationPopup.current?.remove();},[confirmDestination]);
  const fitted=useRef(null);
  const located=useRef(false);
  useEffect(()=>{
    host.current.parentElement.style.setProperty('--sp-location-gap',passengerPosition?'calc(var(--sp-map-control-size,38px) + 10px)':'0px');
  },[!!passengerPosition]);
  const stopCanvas=useRef();
  const markerLayer=useRef(),markerRecords=useRef(new Map());
  click.current=onStop;area.current=onArea;
  useEffect(()=>{
    const instance=L.map(host.current,{zoomSnap:0.1,tapHold:false}).setView([center?.lat??-23.5505,center?.lon??-46.6333],15);
    instance.attributionControl.setPrefix(false).setPosition('topright');
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'}).addTo(instance);
    const longPress=bindMapLongPress(host.current,event=>{
      const point=instance.mouseEventToLatLng(event);
      destinationPopup.current?.remove();
      const coordinates={lat:point.lat,lon:point.lng};
      const controls=document.createElement('div');controls.className='sp-location-popup';
      const button=document.createElement('button');
      button.type='button';button.className='primary';
      button.textContent=confirmPoint.current?'Adicionar como destino':pointRole.current==='origin'?'Usar como embarque':'Usar como destino';
      button.addEventListener('click',()=>{destinationPopup.current?.remove();mapPoint.current?.(coordinates);});
      controls.append(button);
      if(favoritePoint.current){
        const saved=favoriteCheck.current?.(coordinates);
        const star=document.createElement('button');star.type='button';star.className='icon-button sp-favorite-action sp-location-star';
        star.innerHTML='<svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m12 2 3 6 7 1-5 5 1 7-6-3-6 3 1-7-5-5 7-1Z"/></svg>';
        star.setAttribute('data-saved',String(!!saved));star.setAttribute('aria-pressed',String(!!saved));
        star.setAttribute('aria-label',saved?'Remover favorito deste local':'Adicionar local aos favoritos');
        star.title=saved?'Remover favorito':'Salvar local';
        star.addEventListener('click',()=>{destinationPopup.current?.remove();favoritePoint.current?.(coordinates);});
        controls.append(star);
      }
      destinationPopup.current=L.popup().setLatLng(point).setContent(controls).openOn(instance);
    });
    // O movimento do ponteiro aplica a tolerância de 10 px; o Leaflet começa
    // a mover antes disso, o que não deve cancelar uma pressão estável.
    instance.on('zoomstart',longPress.cancel);
    const measurement=L.layerGroup().addTo(instance);
    let measuredPoints=[];
    const clearMeasurement=()=>{measurement.clearLayers();measuredPoints=[];};
    const measure=event=>{
      if(event.button!==2||event.pointerType==='touch')return;
      event.preventDefault();longPress.cancel();
      if(measuredPoints.length===2)clearMeasurement();
      const point=instance.mouseEventToLatLng(event);
      measuredPoints.push(point);
      L.circleMarker(point,{radius:5,color:'#111827',weight:2,fillColor:'#facc15',fillOpacity:1,interactive:false}).addTo(measurement);
      if(measuredPoints.length===1){
        L.tooltip({permanent:true,direction:'top',className:'sp-measure-tooltip'})
          .setLatLng(point).setContent('Clique com o botão direito no ponto final · Esc limpa').addTo(measurement);
        return;
      }
      measurement.eachLayer(layer=>{if(layer instanceof L.Tooltip)measurement.removeLayer(layer);});
      L.polyline(measuredPoints,{color:'#111827',weight:5,interactive:false}).addTo(measurement);
      L.polyline(measuredPoints,{color:'#facc15',weight:3,dashArray:'6 5',interactive:false}).addTo(measurement);
      const meters=measuredPoints[0].distanceTo(point);
      const label=document.createElement('span');
      label.textContent=(meters<1000?Math.round(meters).toLocaleString('pt-BR')+' m':(meters/1000).toLocaleString('pt-BR',{maximumFractionDigits:2})+' km')+' em linha reta ';
      const clear=document.createElement('button');clear.type='button';clear.textContent='×';clear.setAttribute('aria-label','Limpar medição');
      clear.addEventListener('click',event=>{event.stopPropagation();clearMeasurement();});label.append(clear);
      L.tooltip({permanent:true,interactive:true,direction:'top',className:'sp-measure-tooltip'})
        .setLatLng(L.latLng((measuredPoints[0].lat+point.lat)/2,(measuredPoints[0].lng+point.lng)/2))
        .setContent(label).addTo(measurement);
    };
    const clearOnEscape=event=>{if(event.key==='Escape')clearMeasurement();};
    if(developmentTools){
      host.current.addEventListener('contextmenu',measure);
      document.addEventListener('keydown',clearOnEscape);
    }

    let timer;
    const updateArea=()=>{
      clearTimeout(timer);
      timer=setTimeout(()=>{
        const point=instance.getCenter(),bounds=instance.getBounds();
        area.current({lat:point.lat,lon:point.lng,south:bounds.getSouth(),west:Math.max(-180,bounds.getWest()),north:bounds.getNorth(),east:Math.min(180,bounds.getEast())});
      },150);
    };
    instance.on('moveend',updateArea);
    instance.on('moveend zoomend',()=>trace('map_view',{center:instance.getCenter(),zoom:instance.getZoom(),bounds:instance.getBounds()}));
    instance.on('click',e=>trace('map_click',{latlng:e.latlng}));
    updateArea();
    map.current=instance;
    instance.createPane('networkContext');
    instance.getPane('networkContext').style.zIndex='250';
    instance.getPane('networkContext').style.pointerEvents='none';
    instance.createPane('networkLabels');
    instance.getPane('networkLabels').style.zIndex='410';
    instance.getPane('networkLabels').style.pointerEvents='none';
    instance.createPane('passengerLocation');
    instance.getPane('passengerLocation').style.zIndex='750';
    instance.createPane('routeStops');
    instance.getPane('routeStops').style.zIndex='590';
    instance.createPane('busApproach');
    instance.getPane('busApproach').style.zIndex='390';
    instance.getPane('busApproach').style.pointerEvents='none';
    markerLayer.current=L.layerGroup().addTo(instance);
    stopCanvas.current=new StopCanvas(instance,s=>click.current(s));
    const zoomControl=instance.zoomControl.getContainer();
    const alignLocationButton=()=>{
      if(!locationButton.current)return;
      const zoom=zoomControl.getBoundingClientRect();
      const parent=host.current.parentElement.getBoundingClientRect();
      host.current.parentElement.style.setProperty('--sp-map-control-size',`${zoom.width}px`);
      host.current.parentElement.style.setProperty('--sp-map-control-left',`${zoom.left-parent.left}px`);
      host.current.parentElement.style.setProperty('--sp-map-control-top',`${zoom.top-parent.top}px`);
      host.current.parentElement.style.setProperty('--sp-map-control-center',`${zoom.top-parent.top+zoom.height/2}px`);
      host.current.parentElement.style.setProperty('--sp-light-top',`calc(${zoom.bottom-parent.top+10}px + var(--sp-location-gap,0px))`);
      Object.assign(locationButton.current.style,{
        width:`${zoom.width}px`,minWidth:`${zoom.width}px`,maxWidth:`${zoom.width}px`,
        height:`${zoom.width}px`,minHeight:`${zoom.width}px`,maxHeight:`${zoom.width}px`,
        left:`${zoom.left-parent.left}px`,top:`${zoom.bottom-parent.top+10}px`,
      });
    };
    const observer=new ResizeObserver(()=>{instance.invalidateSize();updateArea();alignLocationButton();});
    observer.observe(host.current);observer.observe(zoomControl);
    alignLocationButton();
    return ()=>{host.current?.removeEventListener('contextmenu',measure);document.removeEventListener('keydown',clearOnEscape);measurement.clearLayers();longPress.destroy();instance.off('zoomstart',longPress.cancel);clearTimeout(timer);instance.off('moveend',updateArea);observer.disconnect();markerRecords.current.clear();stopCanvas.current.destroy();instance.remove();};
  },[]);
  useEffect(()=>{
    const controller=new AbortController();
    let removeNetwork;
    api('sptrans/rail-network',{},controller.signal).then(({lines})=>{
      if(controller.signal.aborted)return;
      removeNetwork=drawRailNetwork(map.current,lines||[],()=>stopCanvas.current?.visible||[]);
    }).catch(()=>{/* A rede de contexto não bloqueia a seleção de pontos. */});
    return()=>{controller.abort();removeNetwork?.();};
  },[]);
  useEffect(()=>{stopCanvas.current?.setOpacity(selectingPoint&&transparentStops?1-stopTransparency/100:1);},[selectingPoint,transparentStops,stopTransparency]);
  useEffect(()=>{
    if(!passengerPosition)return;
    const {lat,lon,accuracy,simulated}=passengerPosition;
    const group=L.layerGroup().addTo(map.current);
    if(accuracy>0)L.circle([lat,lon],{radius:accuracy,color:'#0066ff',weight:1,fillOpacity:.1,interactive:false}).addTo(group);
    L.marker([lat,lon],{pane:'passengerLocation',zIndexOffset:1000,title:simulated?'Sua localização (simulada)':'Sua localização',icon:L.divIcon({className:'sp-passenger-position'+(simulated?' is-simulated':''),iconSize:[32,32],iconAnchor:[16,16],html:'<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="8" r="3"/><path d="M6 20v-2a6 6 0 0 1 12 0v2"/></svg>'})})
      .bindTooltip(simulated?'Sua localização (simulada)':'Sua localização').addTo(group);
    if(!located.current&&!preserveViewport&&(!origin||origin.useLocation)){
      located.current=true;
      // Uma área quadrada de 500 m dá raio de 250 m no eixo menor.
      // Mantenha o passageiro centralizado; atualizações GPS posteriores movem apenas o marcador.
      const point=L.latLng(lat,lon);
      const zoom=map.current.getBoundsZoom(point.toBounds(500));
      map.current.setView(point,zoom,{animate:false});
    }
    return ()=>group.remove();
  },[passengerPosition,origin,journey,focusStops]);
  useEffect(()=>{map.current?.fire('railLabelObstaclesChanged');},[passengerPosition,stops,origin,destination,journey,detail,itineraries]);
  useEffect(()=>{
    if(dimmerActive)return;
    const group=L.layerGroup().addTo(map.current);
    const drawRoute=(geometry,foot=false,leg=null)=>{
      if(!geometry?.length)return;
      const options={weight:6,opacity:1,lineCap:'round',lineJoin:'round',dashArray:foot?'9 10':undefined};
      if(isRail(leg))L.polyline(geometry,{...options,weight:12,color:'#111827',className:'sp-rail-outline',interactive:false}).addTo(group);
      L.polyline(geometry,{...options,weight:10,color:'#ffffff',className:isRail(leg)?'sp-rail-halo':'sp-route-halo',interactive:false}).addTo(group);
      L.polyline(geometry,{...options,color:foot?'#d52c94':isRail(leg)?railColor(leg):'#0076ed',className:foot?'sp-route-walk':isRail(leg)?'sp-route-rail':'sp-route-bus'}).bindTooltip(foot?'A pé':isRail(leg)?railLabel(leg):'Ônibus · trajeto GTFS').addTo(group);
    };
    const points=new Map((routeSelected?[]:stops).map(s=>[s.id,s]));
    for(const s of [origin,destination]) if(s) points.set(s.id,{...s,directions:points.get(s.id)?.directions||s.directions});
    for(const leg of journey?.legs||[]) {
      for(const s of [leg.origin,leg.destination]) if(s.id!==destination?.id)points.set(s.id,{...s,mode:s.mode||leg.mode,directions:points.get(s.id)?.directions||s.directions});
      drawRoute(leg.geometry,false,leg);
    }
    for(const path of [walking,...walks].filter(Boolean)) {
      if(path.geometry?.length)drawRoute(path.geometry,true);
    }
    drawRouteStops(group,journey?.legs||[],[origin,destination,...(journey?.legs||[]).flatMap(leg=>[leg.origin,leg.destination])]);
    const ordinary=[];
    for(const s of points.values()) {
      const complete=fullJourney||journey;
      const isOrigin=s.id===(complete?.legs[0]?.origin.id||origin?.id),isDestination=s.id===(destination?.id||complete?.legs.at(-1)?.destination.id);
      const transferIndex=complete?.legs.findIndex((leg,i)=>i>0&&(leg.origin.id===s.id||complete.legs[i-1].destination.id===s.id))??-1;
      const isTransfer=!isOrigin&&!isDestination&&transferIndex>0;
      if(!isOrigin&&!isDestination&&!isTransfer){ordinary.push(s);continue;}
      const markerText=isOrigin?'A':isDestination?'★':isTransfer?String.fromCharCode(65+transferIndex):'';
      const station=isRail(s)&&!s.mapStop;
      const directions=station?[]:s.directions||[];
      const departures=directions.filter(d=>d.kind!=='arrival');
      const markerDirections=departures.length?departures:directions;
      const radius=isOrigin||isDestination?18:isTransfer?14:8;
      const baseX=radius*Math.sqrt(3)/2;
      // A base côncava é um arco da própria circunferência externa do marcador.
      const tipPath=`M0 ${-radius-7} L${baseX} ${-radius/2} A${radius} ${radius} 0 0 0 ${-baseX} ${-radius/2} Z`;
      const directionInfo=directions.map(d=>`${d.code} · ${d.headsign}${d.kind==='arrival'?' (chegada / fim de linha)':''}${d.approximate?' (sentido aproximado)':''}`).join('; ');
      const label=document.createElement('span');label.textContent=(isOrigin?'Origem · ':isDestination?'Destino · ':isTransfer?`Baldeação ${markerText} · `:'')+s.name+(s.mapStop?' · Localização':' · '+s.id+' · '+(station?(s.mode==='metro'?'Estação de metrô':'Estação de trem'):directionInfo||'Sentido indisponível no cadastro'));
      const signature=JSON.stringify([s,isOrigin,isDestination,isTransfer,markerText]);
      const previous=markerRecords.current.get(s.id);
      if(!previous||previous.signature!==signature) {
        if(previous)markerLayer.current.removeLayer(previous.marker);
        const marker=L.marker([s.lat,s.lon],{title:label.textContent,icon:L.divIcon({className:'sp-stop '+(station?'sp-station ':'')+(isOrigin?'sp-origin':isDestination?'sp-destination':isTransfer?'sp-transfer-stop':''),html:(station?stationSymbol+`<span class="sp-station-role">${markerText}</span>`:isOrigin?`<img class="sp-boarding-icon" src="${boardingPointIcon}" alt=""/>`:isDestination?`<img class="sp-destination-icon" src="${destinationPointIcon}" alt=""/>`:markerText)+[...new Set(markerDirections.map(d=>Math.round(d.bearing/20)*20))].map(angle=>`<span class="sp-heading" style="transform:rotate(${Number(angle)}deg)" aria-hidden="true"><svg viewBox="-30 -30 60 60" focusable="false"><path d="${tipPath}"/></svg></span>`).join(''),iconSize:[isOrigin||isDestination?36:isTransfer?28:16,isOrigin||isDestination?36:isTransfer?28:16]})}).bindTooltip(label).on('click',()=>click.current(s)).addTo(markerLayer.current);
        markerRecords.current.set(s.id,{marker,signature});
      }
    }
    stopCanvas.current.setStops(ordinary);
    const ordinaryIds=new Set(ordinary.map(s=>s.id));
    for(const [id,record] of markerRecords.current)if(!points.has(id)||ordinaryIds.has(id)){markerLayer.current.removeLayer(record.marker);markerRecords.current.delete(id);}
    if(detail?.shape?.length) L.polyline(detail.shape,{pane:'networkContext',interactive:false,opacity:isRail(detail.line)?1:.45,color:isRail(detail.line)?railColor({...detail.line,color:detail.line.color||detail.itinerary?.color}):'#4c9aff',weight:5,dashArray:isRail(detail.line)?railDash(false):undefined}).addTo(group);
    for(const v of detail?.vehicles||[]) {
      const label=document.createElement('span');label.textContent=`Ônibus ${v.id} · ${v.code} · posição recebida ${new Date(v.observed_at).toLocaleTimeString('pt-BR')}`;
      L.marker([v.lat,v.lon],{title:label.textContent,icon:L.divIcon({className:'sp-bus',html:'●',iconSize:[22,22]})}).bindTooltip(label).addTo(group);
    }
    return ()=>group.remove();
  },[stops,origin,destination,detail,journey,walking,walks,routeSelected,fullJourney,dimmerActive]);
  useEffect(()=>{
    const group=L.layerGroup().addTo(map.current);
    const strokes=L.layerGroup().addTo(group);
    const redraw=()=>{
      strokes.clearLayers();
      for(const route of itineraries){
        const draw=(points,past)=>{
          if(!points||points.length<2)return;
          const {path,arrows}=directedPath(points.map(p=>map.current.latLngToLayerPoint(p)));
          const railway=isRail(route);
          const color=railway?railColor(route):past?'#a58acb':'#0076ed';
          const dashArray=railway?railDash(past):past?'5 8':undefined;
          const coordinates=path.map(p=>map.current.layerPointToLatLng(L.point(p.x,p.y)));
          if(railway)L.polyline(coordinates,{pane:'networkContext',color:'#475569',weight:past?8:9,opacity:.25,dashArray,interactive:false,className:'sp-rail-halo'}).addTo(strokes);
          L.polyline(coordinates,{pane:'networkContext',color,weight:past?4:5,opacity:railway?1:.45,dashArray,className:(railway?'sp-route-rail ':'')+(past?'sp-line-before':railway?'sp-line-after':'sp-route-bus sp-line-after'),interactive:false}).addTo(strokes);
          for(const arrow of arrows){
            const at=map.current.layerPointToLatLng(L.point(arrow.x,arrow.y));
            L.marker(at,{pane:'networkContext',opacity:railway?1:.45,interactive:false,keyboard:false,icon:L.divIcon({className:`sp-direction-arrow ${past?'sp-direction-before':'sp-direction-after'}`,html:`<span style="transform:rotate(${arrow.angle}deg)${railway?`;color:${color}`:''}">➤</span>`,iconSize:[18,18],iconAnchor:[9,9]})}).addTo(strokes);
          }
        };
        if(route.split_available){draw(route.before,true);draw(route.after,false);}else draw(route.geometry,true);
      }
    };
    redraw();map.current.on('zoomend',redraw);
    drawRouteStops(group,itineraries,[origin,destination,...itineraries.map(route=>{
      const end=route.endpoint||route.terminal;
      return route.geometry?.length&&end?.kind!=='shape'?end:null;
    })]);
    for(const route of itineraries){
      if(route.geometry?.length){
        const label=document.createElement('span');label.textContent=`Início do traçado da linha ${isRail(route)?railLabel(route):route.code||''}`;
        L.marker(route.geometry[0],{title:label.textContent,zIndexOffset:100,icon:L.divIcon({className:'sp-line-start'+(isRail(route)?' sp-stop sp-station':''),html:isRail(route)?stationSymbol+'<span class="sp-station-role">I</span>':'<span aria-hidden="true">I</span>',iconSize:[30,30],iconAnchor:[15,15]})}).bindTooltip(label).addTo(group);
      }
      if((route.endpoint||route.terminal)&&route.geometry?.length){
        const end=route.endpoint||route.terminal,label=document.createElement('span');label.textContent=end.kind==='shape'?`Fim do traçado GTFS da linha ${isRail(route)?railLabel(route):route.code||''} · última parada cadastrada divergente`:`Último ponto da linha ${isRail(route)?railLabel(route):route.code||''} · ${end.name} · ${end.id}`;
        L.marker([end.lat,end.lon],{title:label.textContent,icon:L.divIcon({className:'sp-stop sp-destination sp-line-terminal'+(isRail(route)&&end.kind!=='shape'?' sp-station':''),html:isRail(route)&&end.kind!=='shape'?stationSymbol+'<span class="sp-station-role">★</span>':`<img class="sp-destination-icon" src="${destinationPointIcon}" alt=""/>`,iconSize:[36,36]})}).bindTooltip(label).addTo(group);
      }
    }
    return()=>{map.current.off('zoomend',redraw);group.remove();};
  },[itineraries,origin,destination]);
  const activeApproaches=useMemo(()=>[...(approach?[approach]:[]),...approaches].filter(a=>a?.vehicle),[approach,approaches]);
  const fittedApproach=useRef(null);
  useEffect(()=>{
    if(preserveViewport)return;
    if(!approachFocusKey){fittedApproach.current=null;return;}
    const fitKey=approachFocusKey+':'+itineraries.map(i=>i.trip_id).join(',');
    if((!activeApproaches.length&&!itineraries.some(i=>i.geometry?.length))||fittedApproach.current===fitKey)return;
    const points=[...itineraries.flatMap(i=>i.geometry||[]),...activeApproaches.flatMap(a=>[[a.vehicle.lat,a.vehicle.lon],...(a.geometry||[])]),...(origin?[[origin.lat,origin.lon]]:[])];
    map.current.fitBounds(points,{padding:[60,100],maxZoom:16});
    fittedApproach.current=fitKey;
  },[approachFocusKey,activeApproaches,origin,itineraries]);
  useEffect(()=>{
    const group=L.layerGroup().addTo(map.current),timers=[];
    for(const approach of activeApproaches){
    if(!approach?.vehicle)continue;
    const v=approach.vehicle;
    const vehicleGroup=L.layerGroup().addTo(group);
    const expire=Date.parse(v.observed_at)+180000-Date.now();
    if(!Number.isFinite(expire)||expire<=0){vehicleGroup.remove();continue;}
    if(approach.geometry?.length)L.polyline(approach.geometry,{pane:'busApproach',color:'#a58acb',weight:4,opacity:.55,dashArray:'5 8',interactive:false}).addTo(vehicleGroup);
    const label=document.createElement('span');
    label.textContent=approach.label+' · '+v.code+' · veículo '+v.id+' · posição '+new Date(v.observed_at).toLocaleTimeString('pt-BR');
    L.marker([v.lat,v.lon],{opacity:approach.selection==='passed'?.5:1,zIndexOffset:900,title:label.textContent,icon:L.divIcon({className:'sp-live-bus',iconSize:[32,32],iconAnchor:[16,16],html:'<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="5" y="3" width="14" height="16" rx="3"/><path d="M5 11h14M8 19v2M16 19v2"/><circle cx="8" cy="15" r="1"/><circle cx="16" cy="15" r="1"/></svg>'})}).bindTooltip(label).addTo(vehicleGroup);
    timers.push(setTimeout(()=>vehicleGroup.remove(),expire));
    }
    return()=>{timers.forEach(clearTimeout);group.remove();};
  },[activeApproaches]);
  useEffect(()=>{
    if(routeSelected||preserveViewport)return;
    if(origin && destination && origin.id!==destination.id) map.current.fitBounds([[origin.lat,origin.lon],[destination.lat,destination.lon]],{padding:[40,55],maxZoom:16,animate:false});
    else if(origin) map.current.setView([origin.lat,origin.lon],16,{animate:false});
  },[origin?.id,destination?.id]);
  useEffect(()=>{if(!preserveViewport&&detail?.shape?.length) map.current.fitBounds(detail.shape,{padding:[35,55],animate:false});},[detail?.line?.trip_id]);
  useEffect(()=>{
    if(!journey){fitted.current=null;return;}
    if(preserveViewport||fitted.current===focusKey)return;
    const points=[...journey.legs.flatMap(l=>l.geometry?.length?l.geometry:(l.stops||[l.origin,l.destination]).map(s=>[s.lat,s.lon])),...walks.flatMap(w=>w.geometry||[])];
    if(points.length){map.current.fitBounds(points,{padding:[45,85],animate:false});fitted.current=focusKey;}
  },[journey,walks,focusKey]);
  useEffect(()=>{if(!preserveViewport&&focusStops?.length)map.current.fitBounds(focusStops.map(s=>[s.lat,s.lon]),{padding:[45,65],maxZoom:17,animate:false});},[focusStops]);
  useEffect(()=>{
    if(preserveViewport||!passengerFocus||!map.current)return;
    const point=L.latLng(passengerFocus.lat,passengerFocus.lon);
    map.current.setView(point,map.current.getBoundsZoom(point.toBounds(500)),{animate:false});
  },[passengerFocus]);
  useEffect(()=>{
    if(!coordinateFocus||!map.current)return;
    const point=L.latLng(coordinateFocus.lat,coordinateFocus.lon);
    map.current.setView(point,map.current.getBoundsZoom(point.toBounds(500)),{animate:false});
  },[coordinateFocus]);
  const locatePassenger=()=>{
    if(!passengerPosition||!map.current)return;
    const point=L.latLng(passengerPosition.lat,passengerPosition.lon);
    map.current.setView(point,map.current.getBoundsZoom(point.toBounds(500)),{animate:false});
  };
  const locationLabel=passengerPosition?.simulated?'Minha localização (simulada)':passengerPosition?'Minha localização':'Aguardando localização';
  return <><div ref={host} style={{'--sp-stop-opacity':1-stopTransparency/100}} className={`passenger-map sp-map${selectingPoint&&transparentStops?' sp-transparent-stops':''}`} aria-label="Mapa dos pontos de São Paulo"/>
    {selectingPoint&&<StopTransparencyControl active={transparentStops} onToggle={()=>setTransparentStops(value=>!value)} value={stopTransparency} onChange={changeTransparency} onCommit={commitTransparency} onActiveChange={setDimmerActive}/>}
    <button ref={locationButton} type="button" className="icon-button sp-locate-passenger" style={{display:passengerPosition?undefined:'none'}} onClick={locatePassenger} disabled={!passengerPosition} title={locationLabel} aria-label={locationLabel}><Icon name="locate"/></button></>;

}
