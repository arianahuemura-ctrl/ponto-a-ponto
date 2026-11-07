import L from 'leaflet';
import {railColor,railDash,railLabel,railNumber} from './railStyle.js';

// Neutral outlines keep the official colors readable over either map theme.
// All layers stay below stops and never intercept map selection.
export function drawRailNetwork(map,lines){
  const group=L.layerGroup().addTo(map),labels=L.layerGroup().addTo(group);
  const paths=lines.flatMap(line=>(line.geometries||[]).map(geometry=>({line,geometry})));
  const base={pane:'networkContext',opacity:1,lineCap:'round',lineJoin:'round',interactive:false};
  for(const {geometry} of paths)L.polyline(geometry,{...base,weight:10,color:'#111827',className:'sp-network-rail-halo'}).addTo(group);
  for(const {geometry} of paths)L.polyline(geometry,{...base,weight:8,color:'#ffffff',className:'sp-network-rail-contrast'}).addTo(group);
  for(const {line,geometry} of paths)L.polyline(geometry,{...base,weight:5,color:railColor(line),dashArray:railDash(false),className:'sp-network-rail'}).addTo(group);

  const redrawLabels=()=>{
    labels.clearLayers();
    const size=map.getSize(),center=size.divideBy(2);
    if(size.x<160||size.y<100)return;
    const bounds=L.bounds([70,40],[size.x-70,size.y-40]);
    const choices=lines.map(line=>{
      const points=[];let visibleLength=0;
      for(const geometry of line.geometries||[]){
        const projected=geometry.map(p=>map.latLngToContainerPoint(p));
        for(let i=1;i<projected.length;i++){
          const segment=L.LineUtil.clipSegment(projected[i-1],projected[i],bounds);
          if(!segment)continue;
          const [a,b]=segment,steps=Math.max(1,Math.ceil(a.distanceTo(b)/100));
          visibleLength+=a.distanceTo(b);
          for(let j=0;j<steps;j++)points.push(a.add(b.subtract(a).multiplyBy((j+.5)/steps)));
        }
      }
      return {line,visibleLength,points:points.sort((a,b)=>a.distanceTo(center)-b.distanceTo(center)),placed:[]};
    }).sort((a,b)=>a.visibleLength-b.visibleLength);
    const occupied=[];
    // Give each visible line a label before repeating labels on long stretches.
    for(let pass=0;pass<2;pass++)for(const {line,points,placed} of choices){
      if(occupied.length>=32)break;
      const point=points.find(p=>!occupied.some(q=>Math.abs(p.x-q.x)<104&&Math.abs(p.y-q.y)<38)&&!placed.some(q=>p.distanceTo(q)<340));
      if(!point)continue;
      occupied.push(point);placed.push(point);
      const content=document.createElement('span');
      content.textContent=`${line.mode==='metro'?'Metrô':'Trem'} ${railNumber(line)||line.code||''}`;
      content.style.setProperty('--sp-line-color',railColor(line));
      const title=`${line.mode==='metro'?'Metrô':'Trem'} · ${railLabel(line)}`;
      L.marker(map.containerPointToLatLng(point),{pane:'networkContext',interactive:false,keyboard:false,title,alt:title,
        icon:L.divIcon({className:'sp-network-rail-label',html:content,iconSize:[88,28],iconAnchor:[44,14]})}).addTo(labels);
    }
  };
  redrawLabels();map.on('moveend zoomend resize',redrawLabels);
  return ()=>{map.off('moveend zoomend resize',redrawLabels);group.remove();};
}
