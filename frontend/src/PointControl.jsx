import {useEffect,useId,useRef,useState} from 'react';
import PointIcon from './PointIcon.jsx';

export default function PointControl({kind,point,selecting=false,onClick,disabled=false,collapsible=false}) {
  const [detailsOpen,setDetailsOpen]=useState(false),[held,setHeld]=useState(false);
  const button=useRef(),descriptionId=useId();
  const expanded=!collapsible||detailsOpen;
  useEffect(()=>setDetailsOpen(false),[point?.id,point?.name,point?.destinationAddress,selecting]);
  useEffect(()=>{
    if(!collapsible||!detailsOpen)return;
    const outside=e=>{if(!button.current?.contains(e.target))setDetailsOpen(false);};
    document.addEventListener('pointerdown',outside);
    const timer=held?null:setTimeout(()=>setDetailsOpen(false),8000);
    return()=>{document.removeEventListener('pointerdown',outside);clearTimeout(timer);};
  },[collapsible,detailsOpen,selecting,held]);
  const label=kind==='origin'?'Embarque':'Destino';
  const action=point&&!selecting?`${expanded?'Alterar':'Mostrar'} ${label.toLowerCase()}`:`Selecionar ${label.toLowerCase()}`;
  const state=selecting?'Selecionando':point?'Definido':'Não definido';
  const address=point?.destinationAddress||point?.name;
  const detail=point?.favoriteLabel&&point.favoriteLabel!==address?`${point.favoriteLabel} · ${address}`:address;
  return <button ref={button} type="button" className="icon-button sp-point-control" data-kind={kind} data-state={point?'set':'empty'} data-selecting={selecting} data-collapsed={!expanded}
    aria-label={action} aria-pressed={selecting} aria-expanded={collapsible?expanded:undefined} aria-describedby={descriptionId} disabled={disabled}
    onClick={()=>{if(!expanded){setDetailsOpen(true);return;}setDetailsOpen(false);onClick();}}
    onMouseEnter={()=>setHeld(true)} onMouseLeave={()=>setHeld(document.activeElement===button.current)} onFocus={()=>setHeld(true)} onBlur={()=>setHeld(false)}
    onKeyDown={e=>{if(e.key==='Escape'&&detailsOpen){e.stopPropagation();setDetailsOpen(false);}}}
    title={`${label}: ${detail||'não definido'} · ${state}`}>
    <span className="sp-point-symbol"><PointIcon kind={kind}/><span aria-hidden="true">{selecting?'…':point?'✓':'+'}</span></span>
    <span id={descriptionId} className="sp-point-description" hidden={!expanded}>{label}<small>{detail||(selecting?'Selecione no mapa':'Selecionar local')}</small>
      {collapsible&&expanded&&point&&<span className="sp-point-hint">{selecting?'Escolha outro local no mapa ou na busca':'Toque novamente para alterar'}</span>}
    </span>
  </button>;
}
