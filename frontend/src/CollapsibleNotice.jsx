import {useEffect,useId,useRef,useState} from 'react';
import Icon from './Icon.jsx';

// Keep the message available after collapsing; never remove a focused control.
export default function CollapsibleNotice({message,onDismiss,className='',role='status',label='aviso'}) {
  const [expanded,setExpanded]=useState(true),[held,setHeld]=useState(false);
  const host=useRef(),id=useId();
  useEffect(()=>{setExpanded(true);},[message]);
  useEffect(()=>{
    if(!message||!expanded||held)return;
    const timer=setTimeout(()=>setExpanded(false),8000);
    return()=>clearTimeout(timer);
  },[message,expanded,held]);
  if(!message)return null;
  return <div ref={host} className={`passenger-notice sp-collapsible-notice ${expanded?'is-expanded':'is-collapsed'} ${className}`} onMouseEnter={()=>setHeld(true)} onMouseLeave={()=>setHeld(host.current?.contains(document.activeElement))} onFocus={()=>setHeld(true)} onBlur={e=>{if(!e.currentTarget.contains(e.relatedTarget))setHeld(false);}}>
    <button type="button" className="icon-button" title={expanded?`Recolher ${label}`:message} aria-label={`${expanded?'Recolher':'Mostrar'} ${label}`} aria-expanded={expanded} aria-controls={id} onClick={()=>setExpanded(value=>!value)}><Icon name="info"/></button>
    <span id={id} role={role} hidden={!expanded}>{message}</span>
    {expanded&&onDismiss&&<button type="button" className="icon-button" aria-label="Fechar aviso" onClick={onDismiss}><Icon name="close"/></button>}
  </div>;
}
