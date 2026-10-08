import {useEffect,useRef} from 'react';
export default function CancelTripDialog({open,onConfirm,onClose,boardingOnly=false}) {
  const dialog=useRef(),keep=useRef();
  useEffect(()=>{if(open){dialog.current.showModal();keep.current?.focus();}else dialog.current.close();},[open]);
  return <dialog ref={dialog} className="sp-stop-dialog" aria-labelledby="cancel-trip-title" onCancel={e=>{e.preventDefault();onClose();}}>
    <h2 id="cancel-trip-title">{boardingOnly?'Desmarcar local de embarque?':'Cancelar viagem?'}</h2>
    <p>{boardingOnly?'O local de embarque será desmarcado e você poderá selecionar outro ponto no mapa. Seus favoritos serão mantidos.':'O trajeto atual será removido e os locais de embarque e destino serão desmarcados. Seus favoritos serão mantidos.'}</p>
    <div className="sp-board-actions"><button ref={keep} className="secondary" onClick={onClose}>{boardingOnly?'Manter embarque':'Continuar viagem'}</button><button className="primary" onClick={onConfirm}>Confirmar cancelamento</button></div>
  </dialog>;
}
