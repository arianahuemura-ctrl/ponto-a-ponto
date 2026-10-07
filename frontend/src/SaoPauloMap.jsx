import { useEffect, useRef } from 'react';
import L from 'leaflet';
import Icon from './Icon.jsx';
import {bindMapLongPress} from './mapLongPress.js';
export default function SaoPauloMap({ passengerFocus, passengerPosition, stops, routeSelected=false, focusStops, focusKey, origin, destination, detail, journey, fullJourney, walking, walks=[], center, onStop, onArea, onMapPoint }) {
  const host=useRef(), map=useRef(), click=useRef(onStop), area=useRef(onArea);
  const locationButton=useRef(null), mapPoint=useRef(onMapPoint);
  mapPoint.current=onMapPoint;
  const fitted=useRef(null);
  const located=useRef(false);
  const markerLayer=useRef(),markerRecords=useRef(new Map());
  click.current=onStop;area.current=onArea;
  useEffect(()=>{
    const instance=L.map(host.current,{zoomSnap:0.1,tapHold:false}).setView([center?.lat??-23.5505,center?.lon??-46.6333],15);
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'}).addTo(instance);
    const longPress=bindMapLongPress(host.current,event=>{
      const point=instance.mouseEventToLatLng(event);
      mapPoint.current?.({lat:point.lat,lon:point.lng});
    });
    instance.on('movestart zoomstart',longPress.cancel);
    let timer;
    const updateArea=()=>{
      clearTimeout(timer);
      timer=setTimeout(()=>{
        const point=instance.getCenter(),bounds=instance.getBounds();
        area.current({lat:point.lat,lon:point.lng,south:bounds.getSouth(),west:Math.max(-180,bounds.getWest()),north:bounds.getNorth(),east:Math.min(180,bounds.getEast())});
      },150);
    };
    instance.on('moveend',updateArea);
    updateArea();
    map.current=instance;
    markerLayer.current=L.layerGroup().addTo(instance);
    const zoomControl=instance.zoomControl.getContainer();
    const alignLocationButton=()=>{
      if(!locationButton.current)return;
      const zoom=zoomControl.getBoundingClientRect();
      const parent=locationButton.current.offsetParent.getBoundingClientRect();
      Object.assign(locationButton.current.style,{
        width:`${zoom.width}px`,minWidth:`${zoom.width}px`,maxWidth:`${zoom.width}px`,
        height:`${zoom.width}px`,minHeight:`${zoom.width}px`,maxHeight:`${zoom.width}px`,
        left:`${zoom.left-parent.left}px`,top:`${zoom.bottom-parent.top+10}px`,
      });
    };
    const observer=new ResizeObserver(()=>{instance.invalidateSize();updateArea();alignLocationButton();});
    observer.observe(host.current);observer.observe(zoomControl);
    alignLocationButton();
    return ()=>{longPress.destroy();instance.off('movestart zoomstart',longPress.cancel);clearTimeout(timer);instance.off('moveend',updateArea);observer.disconnect();markerRecords.current.clear();instance.remove();};
  },[]);
  useEffect(()=>{
    if(!passengerPosition)return;
    const {lat,lon,accuracy,simulated}=passengerPosition;
    const group=L.layerGroup().addTo(map.current);
    if(accuracy>0)L.circle([lat,lon],{radius:accuracy,color:'#0066ff',weight:1,fillOpacity:.1,interactive:false}).addTo(group);
    L.marker([lat,lon],{zIndexOffset:1000,title:simulated?'Sua localização (simulada)':'Sua localização',icon:L.divIcon({className:'sp-passenger-position'+(simulated?' is-simulated':''),iconSize:[32,32],iconAnchor:[16,16],html:'<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="8" r="3"/><path d="M6 20v-2a6 6 0 0 1 12 0v2"/></svg>'})})
      .bindTooltip(simulated?'Sua localização (simulada)':'Sua localização').addTo(group);
    if(!located.current){
      located.current=true;
      // A 500 m bounding square gives a 250 m radius on the shorter axis.
      // Keep the passenger exactly centered; later GPS updates only move the marker.
      const point=L.latLng(lat,lon);
      const zoom=map.current.getBoundsZoom(point.toBounds(500));
      map.current.setView(point,zoom,{animate:false});
    }
    return ()=>group.remove();
  },[passengerPosition,origin,journey,focusStops]);
  useEffect(()=>{
    const group=L.layerGroup().addTo(map.current);
    const drawRoute=(geometry,foot=false)=>{
      if(!geometry?.length)return;
      const options={weight:6,opacity:1,lineCap:'round',lineJoin:'round',dashArray:foot?'9 10':undefined};
      L.polyline(geometry,{...options,weight:10,color:'#ffffff',className:'sp-route-halo',interactive:false}).addTo(group);
      L.polyline(geometry,{...options,color:foot?'#d52c94':'#0076ed',className:foot?'sp-route-walk':'sp-route-bus'}).bindTooltip(foot?'A pé':'Ônibus · trajeto GTFS').addTo(group);
    };
    const points=new Map((routeSelected?[]:stops).map(s=>[s.id,s]));
    for(const s of [origin,destination]) if(s) points.set(s.id,{...s,directions:points.get(s.id)?.directions||s.directions});
    for(const leg of journey?.legs||[]) {
      for(const s of [leg.origin,leg.destination]) if(s.id!==destination?.id)points.set(s.id,{...s,directions:points.get(s.id)?.directions||s.directions});
      drawRoute(leg.geometry);
    }
    for(const path of [walking,...walks].filter(Boolean)) {
      if(path.geometry?.length)drawRoute(path.geometry,true);
    }
    for(const s of points.values()) {
      const complete=fullJourney||journey;
      const isOrigin=s.id===(complete?.legs[0]?.origin.id||origin?.id),isDestination=s.id===(destination?.id||complete?.legs.at(-1)?.destination.id);
      const transferIndex=complete?.legs.findIndex((leg,i)=>i>0&&(leg.origin.id===s.id||complete.legs[i-1].destination.id===s.id))??-1;
      const isTransfer=!isOrigin&&!isDestination&&transferIndex>0;
      const markerText=isOrigin?'A':isDestination?'★':isTransfer?String.fromCharCode(65+transferIndex):'';
      const directions=s.directions||[];
      const departures=directions.filter(d=>d.kind!=='arrival');
      const markerDirections=departures.length?departures:directions;
      const radius=isOrigin||isDestination||isTransfer?14:8;
      const baseX=radius*Math.sqrt(3)/2;
      // The concave base is an arc of the marker's own outer circle.
      const tipPath=`M0 ${-radius-7} L${baseX} ${-radius/2} A${radius} ${radius} 0 0 0 ${-baseX} ${-radius/2} Z`;
      const directionInfo=(s.directions||[]).map(d=>`${d.code} · ${d.headsign}${d.kind==='arrival'?' (chegada / fim de linha)':''}${d.approximate?' (sentido aproximado)':''}`).join('; ');
      const label=document.createElement('span');label.textContent=(isOrigin?'Origem · ':isDestination?'Destino · ':isTransfer?`Baldeação ${markerText} · `:'')+s.name+' · '+s.id+' · '+(directionInfo||'Sentido indisponível no cadastro');
      const signature=JSON.stringify([s,isOrigin,isDestination,isTransfer,markerText]);
      const previous=markerRecords.current.get(s.id);
      if(!previous||previous.signature!==signature) {
        if(previous)markerLayer.current.removeLayer(previous.marker);
        const marker=L.marker([s.lat,s.lon],{title:label.textContent,icon:L.divIcon({className:'sp-stop '+(isOrigin?'sp-origin':isDestination?'sp-destination':isTransfer?'sp-transfer-stop':''),html:markerText+[...new Set(markerDirections.map(d=>Math.round(d.bearing/20)*20))].map(angle=>`<span class="sp-heading" style="transform:rotate(${Number(angle)}deg)" aria-hidden="true"><svg viewBox="-30 -30 60 60" focusable="false"><path d="${tipPath}"/></svg></span>`).join(''),iconSize:[isOrigin||isDestination||isTransfer?28:16,isOrigin||isDestination||isTransfer?28:16]})}).bindTooltip(label).on('click',()=>click.current(s)).addTo(markerLayer.current);
        markerRecords.current.set(s.id,{marker,signature});
      }
    }
    for(const [id,record] of markerRecords.current)if(!points.has(id)){markerLayer.current.removeLayer(record.marker);markerRecords.current.delete(id);}
    if(detail?.shape?.length) L.polyline(detail.shape,{color:'#4c9aff',weight:5}).addTo(group);
    for(const v of detail?.vehicles||[]) {
      const label=document.createElement('span');label.textContent=`Ônibus ${v.id} · ${v.code} · posição recebida ${new Date(v.observed_at).toLocaleTimeString('pt-BR')}`;
      L.marker([v.lat,v.lon],{title:label.textContent,icon:L.divIcon({className:'sp-bus',html:'●',iconSize:[22,22]})}).bindTooltip(label).addTo(group);
    }
    return ()=>group.remove();
  },[stops,origin,destination,detail,journey,walking,walks,routeSelected,fullJourney]);
  useEffect(()=>{
    if(routeSelected)return;
    if(origin && destination && origin.id!==destination.id) map.current.fitBounds([[origin.lat,origin.lon],[destination.lat,destination.lon]],{padding:[40,55],maxZoom:16,animate:false});
    else if(origin) map.current.setView([origin.lat,origin.lon],16,{animate:false});
  },[origin?.id,destination?.id]);
  useEffect(()=>{if(detail?.shape?.length) map.current.fitBounds(detail.shape,{padding:[35,55],animate:false});},[detail?.line?.trip_id]);
  useEffect(()=>{
    if(!journey){fitted.current=null;return;}
    if(fitted.current===focusKey)return;
    const points=[...journey.legs.flatMap(l=>l.geometry?.length?l.geometry:(l.stops||[l.origin,l.destination]).map(s=>[s.lat,s.lon])),...walks.flatMap(w=>w.geometry||[])];
    if(points.length){map.current.fitBounds(points,{padding:[45,85],animate:false});fitted.current=focusKey;}
  },[journey,walks,focusKey]);
  useEffect(()=>{if(focusStops?.length)map.current.fitBounds(focusStops.map(s=>[s.lat,s.lon]),{padding:[45,65],maxZoom:17,animate:false});},[focusStops]);
  useEffect(()=>{
    if(!passengerFocus||!map.current)return;
    const point=L.latLng(passengerFocus.lat,passengerFocus.lon);
    map.current.setView(point,map.current.getBoundsZoom(point.toBounds(500)),{animate:false});
  },[passengerFocus]);
  const locatePassenger=()=>{
    if(!passengerPosition||!map.current)return;
    const point=L.latLng(passengerPosition.lat,passengerPosition.lon);
    map.current.setView(point,map.current.getBoundsZoom(point.toBounds(500)),{animate:false});
  };
  const locationLabel=passengerPosition?.simulated?'Minha localização (simulada)':passengerPosition?'Minha localização':'Aguardando localização';
  return <><div ref={host} className="passenger-map sp-map" aria-label="Mapa dos pontos de São Paulo"/>
    <button ref={locationButton} type="button" className="icon-button sp-locate-passenger" onClick={locatePassenger} disabled={!passengerPosition} title={locationLabel} aria-label={locationLabel}><Icon name="locate"/></button></>;

}
