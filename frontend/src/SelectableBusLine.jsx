import {useEffect,useRef} from 'react';

export default function SelectableBusLine({line,selecting,checked,onSelect,onWatch,children}) {
  const gesture=useRef(null),timer=useRef(null),suppressed=useRef(false);
  const clear=()=>{clearTimeout(timer.current);gesture.current=null;};
  useEffect(()=>{
    const move=e=>{const p=gesture.current;if(p&&(p.id!==e.pointerId||Math.hypot(e.clientX-p.x,e.clientY-p.y)>10))clear();};
    window.addEventListener('pointermove',move,true);
    window.addEventListener('pointerup',clear,true);
    window.addEventListener('pointercancel',clear,true);
    window.addEventListener('blur',clear);
    window.addEventListener('scroll',clear,true);
    return()=>{clear();window.removeEventListener('pointermove',move,true);window.removeEventListener('pointerup',clear,true);window.removeEventListener('pointercancel',clear,true);window.removeEventListener('blur',clear);window.removeEventListener('scroll',clear,true);};
  },[]);
  return <article className={selecting?'sp-selectable-line selecting':'sp-selectable-line'}
    tabIndex={selecting?undefined:0}
    aria-label={'Ver próximos ônibus da linha '+line.code}
    onKeyDown={e=>{if(e.target===e.currentTarget&&(e.key==='Enter'||e.key===' ')){e.preventDefault();if(selecting)onSelect(line);else onWatch?.(line);}}}
    onClick={e=>{if(!selecting&&!e.target.closest('button,a,input'))onWatch?.(line);}}
    onContextMenu={e=>e.preventDefault()}
    onPointerDown={e=>{
      clear();suppressed.current=false;
      if(!e.isPrimary||e.button!==0||e.target.closest('input'))return;
      gesture.current={id:e.pointerId,x:e.clientX,y:e.clientY};
      timer.current=setTimeout(()=>{clear();suppressed.current=true;onSelect(line);},650);
    }}
    onClickCapture={e=>{
      if(suppressed.current){suppressed.current=false;e.preventDefault();e.stopPropagation();return;}
      if(selecting&&!e.target.closest('input')){e.preventDefault();e.stopPropagation();onSelect(line);}
    }}>
    {selecting&&<input className="sp-line-checkbox" type="checkbox" aria-label={'Acompanhar linha '+line.code+' · '+line.headsign} checked={checked} onChange={()=>onSelect(line)}/>}
    {children}
  </article>;
}
