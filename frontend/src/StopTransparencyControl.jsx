import {useEffect, useRef, useState} from 'react';
import Icon from './Icon.jsx';

export default function StopTransparencyControl({active, onToggle, value, onChange, onCommit=onChange, onActiveChange}) {
  const [open,setOpen]=useState(false), [bounds,setBounds]=useState({});
  const root=useRef(null), button=useRef(null), bar=useRef(null), timer=useRef(null), held=useRef(false), opened=useRef(false);
  const cancel=()=>clearTimeout(timer.current);
  const close=()=>{cancel();opened.current=false;root.current?.parentElement.classList.remove('sp-dimming');setOpen(false);onActiveChange?.(false);};
  const show=()=>{
    const map=root.current.parentElement;
    const controls=[...map.querySelectorAll('.leaflet-control-zoom,.sp-locate-passenger,.sp-stop-transparency,.sp-map-point-controls')];
    const rects=controls.map(e=>e.getBoundingClientRect()).filter(r=>r.height);
    const origin=map.getBoundingClientRect(), lamp=button.current.getBoundingClientRect();
    setBounds({top:Math.min(...rects.map(r=>r.top))-origin.top,left:lamp.left-origin.left,width:lamp.width,height:Math.max(...rects.map(r=>r.bottom))-Math.min(...rects.map(r=>r.top))});
    held.current=true;opened.current=true;setOpen(true);
  };
  const select=y=>{const r=bar.current.getBoundingClientRect();const next=Math.round(Math.max(0,Math.min(100,(y-r.top)/r.height*100)));onChange(next);return next;};
  const finish=y=>{
    cancel();
    if(!opened.current)return;
    try { onCommit(select(y)); } finally { close(); }
  };
  useEffect(()=>{
    if(!open)return;
    const release=e=>finish(e.clientY);
    const interrupt=()=>close();
    const hidden=()=>{if(document.hidden)close();};
    // Capture release even when the pointer is over the map or capture is lost.
    window.addEventListener('pointerup',release,true);
    window.addEventListener('pointercancel',interrupt,true);
    window.addEventListener('blur',interrupt);
    document.addEventListener('visibilitychange',hidden);
    return()=>{window.removeEventListener('pointerup',release,true);window.removeEventListener('pointercancel',interrupt,true);window.removeEventListener('blur',interrupt);document.removeEventListener('visibilitychange',hidden);};
  },[open,onCommit]);
  useEffect(()=>()=>{clearTimeout(timer.current);onActiveChange?.(false);},[onActiveChange]);
  useEffect(()=>{onActiveChange?.(open);const map=root.current.parentElement;map.classList.toggle('sp-dimming',open);return()=>map.classList.remove('sp-dimming');},[open,onActiveChange]);
  return <div ref={root} onKeyDown={e=>{if(e.key==='Escape')close();}}>
    <button ref={button} type="button" className="icon-button sp-stop-transparency" aria-label="Pontos transparentes" aria-pressed={active} aria-expanded={open}
      title="Clique para alternar. Segure e arraste para ajustar a transparência."
      onPointerDown={e=>{if(e.button!==0)return;cancel();held.current=false;e.currentTarget.setPointerCapture(e.pointerId);timer.current=setTimeout(show,600);}}
      onPointerMove={e=>{if(held.current&&open)select(e.clientY);}}
      onPointerUp={e=>finish(e.clientY)}
      onPointerCancel={()=>{cancel();close();held.current=true;}}
      onLostPointerCapture={()=>{if(opened.current)close();else cancel();}}
      onContextMenu={e=>e.preventDefault()}
      onKeyDown={e=>{if(e.key==='ArrowDown'){e.preventDefault();show();setTimeout(()=>bar.current.focus(),0);}}}
      onClick={()=>{if(held.current){held.current=false;return;}onToggle();}}
    ><Icon name={active?'bulbOff':'bulb'}/></button>
    <div ref={bar} role="slider" tabIndex={open?0:-1} aria-label="Transparência dos pontos" aria-valuemin={0} aria-valuemax={100} aria-valuenow={value} aria-orientation="vertical" aria-hidden={!open}
      className={`sp-dimmer-bar${open?' is-open':''}`} style={bounds}
      onPointerCancel={()=>close()}
      onLostPointerCapture={()=>{if(opened.current)close();}}
      onPointerDown={e=>{e.currentTarget.setPointerCapture(e.pointerId);select(e.clientY);}}
      onPointerMove={e=>{if(e.buttons===1)select(e.clientY);}}
      onPointerUp={e=>finish(e.clientY)}
      onKeyDown={e=>{if(['ArrowUp','ArrowDown','Home','End'].includes(e.key)){e.preventDefault();onChange(e.key==='Home'?0:e.key==='End'?100:Math.max(0,Math.min(100,value+(e.key==='ArrowDown'?1:-1))));}if(e.key==='Enter'){onCommit(value);close();button.current.focus();}}}
    ><span className="sp-dimmer-thumb" style={{top:`${value}%`}}/></div>
  </div>;
}
