import { useEffect, useRef } from 'react';
import L from 'leaflet';
export default function SaoPauloMap({ stops, routeSelected=false, focusStops, origin, destination, detail, journey, fullJourney, walking, walks=[], center, onStop, onArea }) {
  const host=useRef(), map=useRef(), click=useRef(onStop), area=useRef(onArea);
  const markerLayer=useRef(),markerRecords=useRef(new Map());
  click.current=onStop;area.current=onArea;
  useEffect(()=>{
    const instance=L.map(host.current).setView([center?.lat??-23.5505,center?.lon??-46.6333],15);
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'}).addTo(instance);
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
    const observer=new ResizeObserver(()=>{instance.invalidateSize();updateArea();});observer.observe(host.current);
    return ()=>{clearTimeout(timer);instance.off('moveend',updateArea);observer.disconnect();markerRecords.current.clear();instance.remove();};
  },[]);
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
      for(const s of [leg.origin,leg.destination]) points.set(s.id,{...s,directions:points.get(s.id)?.directions||s.directions});
      drawRoute(leg.geometry);
    }
    for(const path of [walking,...walks].filter(Boolean)) {
      if(path.geometry?.length)drawRoute(path.geometry,true);
    }
    for(const s of points.values()) {
      const complete=fullJourney||journey;
      const isOrigin=s.id===(complete?.legs[0]?.origin.id||origin?.id),isDestination=s.id===(complete?.legs.at(-1)?.destination.id||destination?.id);
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
    if(origin && destination && origin.id!==destination.id) map.current.fitBounds([[origin.lat,origin.lon],[destination.lat,destination.lon]],{padding:[40,55],maxZoom:16,animate:false});
    else if(origin) map.current.setView([origin.lat,origin.lon],16,{animate:false});
  },[origin?.id,destination?.id]);
  useEffect(()=>{if(detail?.shape?.length) map.current.fitBounds(detail.shape,{padding:[35,55],animate:false});},[detail?.line?.trip_id]);
  useEffect(()=>{
    const points=journey?.legs.flatMap(l=>l.geometry?.length?l.geometry:l.stops.map(s=>[s.lat,s.lon]));
    if(points?.length)map.current.fitBounds(points,{padding:[40,55],animate:false});
  },[journey]);
  useEffect(()=>{if(walking?.geometry?.length)map.current.fitBounds(walking.geometry,{padding:[40,55],animate:false});},[walking]);
  useEffect(()=>{if(focusStops?.length)map.current.fitBounds(focusStops.map(s=>[s.lat,s.lon]),{padding:[45,65],maxZoom:17,animate:false});},[focusStops]);
  useEffect(()=>{
    if(!walks.length)return;
    const points=[...(journey?.legs.flatMap(l=>l.geometry||[])||[]),...walks.flatMap(w=>w.geometry||[])];
    if(points.length)map.current.fitBounds(points,{padding:[45,85],animate:false});
  },[walks,journey]);
  return <div ref={host} className="passenger-map sp-map" aria-label="Mapa dos pontos de São Paulo"/>;
}
