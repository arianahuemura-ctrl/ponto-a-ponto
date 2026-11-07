import L from 'leaflet';
import {railColor,railDash,railMapLabel} from './railStyle.js';
import {placeRailLabels,labelBox} from './railLabelLayout.js';

// Neutral outlines keep the official colors readable over either map theme.
// All layers stay below stops and never intercept map selection.
export function drawRailNetwork(map,lines,getStops=()=>[]){
  const group=L.layerGroup().addTo(map),labels=L.layerGroup().addTo(group);
  const paths=lines.flatMap(line=>(line.geometries||[]).map(geometry=>({line,geometry})));
  const base={pane:'networkContext',opacity:1,lineCap:'round',lineJoin:'round',interactive:false};
  for(const {geometry} of paths)L.polyline(geometry,{...base,weight:10,color:'#111827',className:'sp-network-rail-halo'}).addTo(group);
  for(const {geometry} of paths)L.polyline(geometry,{...base,weight:8,color:'#ffffff',className:'sp-network-rail-contrast'}).addTo(group);
  for(const {line,geometry} of paths)L.polyline(geometry,{...base,weight:5,color:railColor(line),dashArray:railDash(false),className:'sp-network-rail'}).addTo(group);

  const redrawLabels=()=>{
    labels.clearLayers();
    const size=map.getSize(),host=map.getContainer(),bounds=host.getBoundingClientRect();
    const obstacles=getStops().map(s=>labelBox(map.latLngToContainerPoint([s.lat,s.lon]),28,28));
    for(const node of host.querySelectorAll('.sp-passenger-position,.sp-origin,.sp-destination,.sp-transfer-stop,.sp-route-stop,.leaflet-control')){
      const rect=node.getBoundingClientRect();if(!rect.width||!rect.height)continue;
      const gap=node.classList.contains('sp-passenger-position')?18:8;
      obstacles.push({left:rect.left-bounds.left-gap,right:rect.right-bounds.left+gap,
        top:rect.top-bounds.top-gap,bottom:rect.bottom-bounds.top+gap});
    }
    const measure=document.createElement('canvas').getContext('2d');measure.font='800 13px Arial';
    const choices=lines.map(line=>{
      const label=railMapLabel(line),fullWidth=Math.ceil(measure.measureText(label).width)+24;
      const width=Math.min(fullWidth,size.x<600?126:220),height=width<fullWidth?46:30;
      return {...line,label,width,height,geometries:(line.geometries||[]).map(g=>g.map(p=>map.latLngToContainerPoint(p)))};
    });
    for(const {line,anchor,point,edge} of placeRailLabels(choices,{width:size.x,height:size.y,obstacles})){
      const content=document.createElement('span');
      content.textContent=line.label;
      content.style.setProperty('--sp-line-color',railColor(line));
      const toLatLng=p=>map.containerPointToLatLng(L.point(p.x,p.y));
      L.polyline([toLatLng(anchor),toLatLng(edge)],{pane:'networkLabels',color:'#475569',weight:1.5,opacity:1,
        interactive:false,className:'sp-network-rail-label-link'}).addTo(labels);
      L.marker(toLatLng(point),{pane:'networkLabels',interactive:false,keyboard:false,title:line.label,alt:line.label,
        icon:L.divIcon({className:'sp-network-rail-label',html:content,iconSize:[line.width,line.height],iconAnchor:[line.width/2,line.height/2]})}).addTo(labels);
    }
  };
  let frame;
  const schedule=()=>{cancelAnimationFrame(frame);frame=requestAnimationFrame(redrawLabels);};
  schedule();map.on('moveend zoomend resize railLabelObstaclesChanged',schedule);
  return ()=>{cancelAnimationFrame(frame);map.off('moveend zoomend resize railLabelObstaclesChanged',schedule);group.remove();};
}
