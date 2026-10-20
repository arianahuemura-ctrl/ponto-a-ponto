import {useEffect,useState} from 'react';
export default function FullscreenButton({onError}){
  const [active,setActive]=useState(!!document.fullscreenElement);
  const [busy,setBusy]=useState(false);
  useEffect(()=>{
    const update=()=>setActive(!!document.fullscreenElement);
    document.addEventListener('fullscreenchange',update);
    return()=>document.removeEventListener('fullscreenchange',update);
  },[]);
  if(!document.fullscreenEnabled||!document.documentElement.requestFullscreen)return null;
  const label=active?'Sair da tela cheia':'Entrar em tela cheia';
  const toggle=async()=>{
    setBusy(true);
    try{
      if(document.fullscreenElement)await document.exitFullscreen();
      else await document.documentElement.requestFullscreen();
    }catch{onError('Não foi possível ativar ou sair da tela cheia neste navegador.');}
    finally{setBusy(false);}
  };
  return <button type="button" className="icon-button" title={label} aria-label={label} aria-pressed={active} disabled={busy} onClick={toggle}>
    <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d={active?'M3 8h5V3m8 0v5h5M3 16h5v5m8 0v-5h5':'M8 3H3v5m13-5h5v5M3 16v5h5m8 0h5v-5'}/>
    </svg>
  </button>;
}
