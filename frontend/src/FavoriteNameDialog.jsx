import {useEffect,useRef,useState} from 'react';
import Icon from './Icon.jsx';
export default function FavoriteNameDialog({stop,onSave,onClose}) {
  const dialog=useRef(),input=useRef();
  const [name,setName]=useState('');
  useEffect(()=>{
    if(stop){setName(stop.favoriteLabel||stop.name);dialog.current.showModal();input.current?.focus();input.current?.select();}
    else dialog.current.close();
  },[stop]);
  return <dialog ref={dialog} className="sp-stop-dialog" aria-labelledby="favorite-name-title" onCancel={onClose}>
    <h2 id="favorite-name-title">Nome do favorito</h2>
    <p>{stop?.name} · {stop?.id}</p>
    <form onSubmit={e=>{e.preventDefault();if(name.trim())onSave(name.trim());}}>
      <label className="sp-search-label">Nome do favorito<input ref={input} value={name} onChange={e=>setName(e.target.value)} maxLength={80} required placeholder="Ex.: Casa, Trabalho, Faculdade"/></label>
      <div className="sp-board-actions"><button type="submit" className="primary" disabled={!name.trim()}><Icon name="star"/> Salvar favorito</button><button type="button" className="text-button" onClick={onClose}>Cancelar</button></div>
    </form>
  </dialog>;
}
