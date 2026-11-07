import {useEffect,useRef,useState} from 'react';
import {quickDestinationLabels} from './QuickDestinations.jsx';
export default function QuickDestinationDialog({role,favorites,assignments,onSave,onClose}) {
  const dialog=useRef();const [point,setPoint]=useState('');
  useEffect(()=>{
    if(role){setPoint(assignments[role]||'');if(!dialog.current.open)dialog.current.showModal();}
    else if(dialog.current.open)dialog.current.close();
  },[role,assignments]);
  const label=quickDestinationLabels[role]||'';
  return <dialog ref={dialog} className="sp-stop-dialog" aria-labelledby="quick-destination-title" onCancel={onClose}>
    <h2 id="quick-destination-title">Configurar {label}</h2>
    <p>Escolha o favorito que será usado como destino ao tocar em {label} na tela inicial.</p>
    {!favorites.length&&<p>Primeiro salve uma parada ou localização usando a estrela. Depois volte aqui para configurar o atalho.</p>}
    <form onSubmit={e=>{e.preventDefault();onSave(role,point);}}>
      <label className="sp-search-label">Local de {label}<select value={point} onChange={e=>setPoint(e.target.value)}><option value="">Sem atalho</option>{favorites.map(s=><option key={s.id} value={s.id}>{s.favoriteLabel||s.name} · {s.kind==='location'?'Localização':s.id}</option>)}</select></label>
      {assignments[role]&&<p>Alterar ou retirar este atalho não remove o local dos favoritos.</p>}
      <div className="sp-board-actions"><button type="submit" className="primary" disabled={!point&&!assignments[role]}>Salvar atalho</button><button type="button" className="text-button" onClick={onClose}>Cancelar</button></div>
    </form>
  </dialog>;
}
