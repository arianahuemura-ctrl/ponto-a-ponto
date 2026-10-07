import {useEffect,useRef} from 'react';
export default function CancelTripDialog({open,onConfirm,onClose}) {
  const dialog=useRef(),keep=useRef();
  useEffect(()=>{if(open){dialog.current.showModal();keep.current?.focus();}else dialog.current.close();},[open]);
  return <dialog ref={dialog} className="sp-stop-dialog" aria-labelledby="cancel-trip-title" onCancel={e=>{e.preventDefault();onClose();}}>
    <h2 id="cancel-trip-title">Cancelar viagem?</h2>
    <p>O embarque, o destino e o trajeto atual serão limpos. Seus favoritos serão mantidos.</p>
    <div className="sp-board-actions"><button ref={keep} className="secondary" onClick={onClose}>Continuar viagem</button><button className="primary" onClick={onConfirm}>Confirmar cancelamento</button></div>
  </dialog>;
}
