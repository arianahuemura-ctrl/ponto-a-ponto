import L from 'leaflet';

// One bitmap layer, reusable symbols and a pixel grid for hit testing.
export class StopCanvas {
  constructor(map,onSelect){
    this.map=map;this.onSelect=onSelect;this.stops=[];this.sprites=new Map();this.grid=new Map();
    this.canvas=L.DomUtil.create('canvas','sp-stop-canvas leaflet-zoom-animated',map.getContainer());
    Object.assign(this.canvas.style,{position:'absolute',inset:'0',zIndex:401,pointerEvents:'none',transformOrigin:'0 0'});
    this.canvas.tabIndex=0;this.canvas.setAttribute('role','group');this.canvas.setAttribute('aria-label','Pontos de ônibus. Use as setas para escolher e Enter para selecionar.');
    this.keyboardIndex=-1;this.visible=[];
    this.key=e=>{if(['ArrowRight','ArrowDown','ArrowLeft','ArrowUp'].includes(e.key)&&this.visible.length){e.preventDefault();this.keyboardIndex=(this.keyboardIndex+(e.key==='ArrowLeft'||e.key==='ArrowUp'?-1:1)+this.visible.length)%this.visible.length;const s=this.visible[this.keyboardIndex];this.canvas.setAttribute('aria-label',s.name+' · '+s.id);this.hover({containerPoint:this.map.latLngToContainerPoint([s.lat,s.lon])});}else if(e.key==='Enter'&&this.visible[this.keyboardIndex]){e.preventDefault();this.onSelect(this.visible[this.keyboardIndex]);}};this.canvas.addEventListener('keydown',this.key);
    this.schedule=()=>{if(!this.frame)this.frame=requestAnimationFrame(()=>{this.frame=0;if(!this.zooming)this.draw();});};
    this.click=e=>{if(e.originalEvent?.target.closest('.leaflet-marker-icon,.leaflet-control'))return;const s=this.hit(e.containerPoint);if(s)this.onSelect(s);};
    this.hover=e=>{const s=this.hit(e.containerPoint);if(s===this.hovered)return;this.hovered=s;if(this.tooltip){map.removeLayer(this.tooltip);this.tooltip=null;}if(s){const label=document.createElement('span');label.textContent=s.name+' · '+s.id+((s.directions||[]).length?' · '+s.directions.map(d=>`${d.code||''} ${d.headsign||''}`.trim()).filter(Boolean).join('; '):'');this.tooltip=L.tooltip().setLatLng([s.lat,s.lon]).setContent(label).addTo(map);}};
    this.zoomStart=()=>{this.zooming=true;cancelAnimationFrame(this.frame);this.frame=0;if(this.tooltip){map.removeLayer(this.tooltip);this.tooltip=null;this.hovered=null;}};
    this.zoomFrame=()=>this.transform(map.getCenter(),map.getZoom(),false);
    this.zoomAnim=e=>this.transform(e.center,e.zoom,true);
    this.zoomEnd=()=>{this.zooming=false;this.draw();};
    map.on('zoomstart',this.zoomStart);map.on('zoomanim',this.zoomAnim);map.on('zoom',this.zoomFrame);map.on('zoomend',this.zoomEnd);
    map.on('move resize',this.schedule);map.on('click',this.click);map.on('mousemove',this.hover);
  }
  transform(center,zoom,animated){
    if(this.renderZoom===undefined)return;
    const scale=this.map.getZoomScale(zoom,this.renderZoom);
    const offset=this.map.project(this.renderCenter,zoom).subtract(this.map.project(center,zoom))
      .add(this.map.getSize().divideBy(2)).subtract(this.renderSize.multiplyBy(scale/2));
    this.canvas.style.transition=animated?'transform 250ms cubic-bezier(0,0,0.25,1)':'none';
    L.DomUtil.setTransform(this.canvas,offset,scale);
  }
  setStops(stops){this.stops=stops;this.schedule();}
  setOpacity(value){this.canvas.style.opacity=String(value);}
  sprite(stop,dpr){
    const dirs=stop.directions||[],departures=dirs.filter(d=>d.kind!=='arrival');
    const angles=[...new Set((departures.length?departures:dirs).map(d=>Math.round(d.bearing/20)*20))].sort((a,b)=>a-b);
    const key=dpr+':'+angles.join(',');if(this.sprites.has(key))return this.sprites.get(key);
    const c=document.createElement('canvas');c.width=c.height=40*dpr;const ctx=c.getContext('2d');ctx.scale(dpr,dpr);ctx.translate(20,20);
    ctx.fillStyle='#1372db';ctx.strokeStyle='white';ctx.lineWidth=2;
    for(const angle of angles){ctx.save();ctx.rotate(angle*Math.PI/180);ctx.beginPath();ctx.moveTo(0,-15);ctx.lineTo(6.93,-4);ctx.quadraticCurveTo(0,-8,-6.93,-4);ctx.closePath();ctx.fill();ctx.restore();}
    ctx.beginPath();ctx.arc(0,0,7,0,Math.PI*2);ctx.fill();ctx.stroke();
    if(this.sprites.size>256)this.sprites.clear();this.sprites.set(key,c);return c;
  }
  draw(){
    if(this.zooming)return;
    const start=performance.now(),size=this.map.getSize(),dpr=window.devicePixelRatio||1,c=this.canvas;
    if(c.width!==Math.round(size.x*dpr)||c.height!==Math.round(size.y*dpr)){c.width=Math.round(size.x*dpr);c.height=Math.round(size.y*dpr);c.style.width=size.x+'px';c.style.height=size.y+'px';}
    const ctx=c.getContext('2d');ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,size.x,size.y);this.grid.clear();this.visible=[];let count=0;
    for(const s of this.stops){const p=this.map.latLngToContainerPoint([s.lat,s.lon]);if(p.x < -20||p.y < -20||p.x>size.x+20||p.y>size.y+20)continue;
      this.visible.push(s);ctx.drawImage(this.sprite(s,dpr),p.x-20,p.y-20,40,40);const key=Math.floor(p.x/32)+':'+Math.floor(p.y/32);if(!this.grid.has(key))this.grid.set(key,[]);this.grid.get(key).push({s,p});count++;
    }
    // Replace the scaled bitmap and reset its transform together, before paint.
    c.style.transition='none';L.DomUtil.setTransform(c,L.point(0,0),1);
    this.renderZoom=this.map.getZoom();this.renderCenter=this.map.getCenter();this.renderSize=size.clone();
    c.dataset.points=String(count);c.dataset.drawMs=(performance.now()-start).toFixed(2);
  }
  hit(point){if(this.zooming)return null;let best=null,distance=144;const x=Math.floor(point.x/32),y=Math.floor(point.y/32);
    for(let dx=-1;dx<=1;dx++)for(let dy=-1;dy<=1;dy++)for(const {s,p} of this.grid.get((x+dx)+':'+(y+dy))||[]){const d=(p.x-point.x)**2+(p.y-point.y)**2;if(d<=distance){best=s;distance=d;}}
    return best;
  }
  destroy(){cancelAnimationFrame(this.frame);this.map.off('move resize',this.schedule);this.map.off('zoomstart',this.zoomStart);this.map.off('zoomanim',this.zoomAnim);this.map.off('zoom',this.zoomFrame);this.map.off('zoomend',this.zoomEnd);this.map.off('click',this.click);this.map.off('mousemove',this.hover);if(this.tooltip)this.map.removeLayer(this.tooltip);this.canvas.removeEventListener('keydown',this.key);this.canvas.remove();this.sprites.clear();this.grid.clear();}
}
