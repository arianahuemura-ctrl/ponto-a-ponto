import {useEffect,useRef} from 'react';
export default function RemoveFavoriteDialog({stop,onConfirm,onClose}) {
  const dialog=useRef(),cancel=useRef();
  useEffect(()=>{
    if(stop){dialog.current.showModal();cancel.current?.focus();}
    else dialog.current.close();
  },[stop]);
  return <dialog ref={dialog} className="sp-stop-dialog" aria-labelledby="remove-favorite-title" aria-describedby="remove-favorite-description" onCancel={e=>{e.preventDefault();onClose();}}>
    <h2 id="remove-favorite-title">Remover favorito?</h2>
    <p id="remove-favorite-description">Deseja remover “{stop?.favoriteLabel||stop?.name}” dos seus favoritos?</p>
    <p>{stop?.name} · {stop?.id}</p>
    <div className="sp-board-actions"><button ref={cancel} className="secondary" onClick={onClose}>Cancelar</button><button className="primary" onClick={onConfirm}>Remover favorito</button></div>
  </dialog>;
}
