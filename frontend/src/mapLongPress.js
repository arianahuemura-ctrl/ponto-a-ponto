// Eventos de ponteiro aceitam toque, caneta e mouse sem bloquear o arrasto do Leaflet.
export function bindMapLongPress(element, onSelect, {delay=650, tolerance=10}={}) {
  const pointers=new Set();
  let timer, start, suppressUntil=0;
  const cancel=()=>{clearTimeout(timer);timer=null;start=null;};
  const down=e=>{
    pointers.add(e.pointerId);
    cancel();
    if(pointers.size!==1||e.button!==0||e.target.closest('.leaflet-control, .leaflet-marker-icon, button, a, input, select'))return;
    suppressUntil=0;
    start={id:e.pointerId,x:e.clientX,y:e.clientY};
    timer=setTimeout(()=>{
      const point=start;
      cancel();
      suppressUntil=Date.now()+1200;
      onSelect({clientX:point.x,clientY:point.y});
    },delay);
  };
  const move=e=>{
    if(start&&e.pointerId===start.id&&Math.hypot(e.clientX-start.x,e.clientY-start.y)>tolerance)cancel();
  };
  const up=e=>{pointers.delete(e.pointerId);cancel();};
  const reset=()=>{pointers.clear();cancel();};
  const click=e=>{if(Date.now()<suppressUntil){e.preventDefault();e.stopImmediatePropagation();}};
  const context=e=>{e.preventDefault();}; // No native long-touch menu on mobile.
  const win=element.ownerDocument.defaultView;
  element.addEventListener('pointerdown',down,true);
  win.addEventListener('pointermove',move,true);
  win.addEventListener('pointerup',up,true);
  win.addEventListener('pointercancel',up,true);
  win.addEventListener('blur',reset);
  win.addEventListener('click',click,true);
  element.addEventListener('contextmenu',context);
  return {cancel, destroy(){
    reset();
    element.removeEventListener('pointerdown',down,true);
    win.removeEventListener('pointermove',move,true);
    win.removeEventListener('pointerup',up,true);
    win.removeEventListener('pointercancel',up,true);
    win.removeEventListener('blur',reset);
    win.removeEventListener('click',click,true);
    element.removeEventListener('contextmenu',context);
  }};
}
