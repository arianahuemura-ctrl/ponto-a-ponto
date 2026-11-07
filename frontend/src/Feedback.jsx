import './dialogControls.css';
import {useRef,useState,useEffect} from 'react';
import {prepareFeedback,submitFeedback} from './usability.js';
import './feedback.css';
export default function Feedback(){
  const dialog=useRef(),trigger=useRef(),pending=useRef(),backdropPress=useRef(null);
  const [message,setMessage]=useState(''),[category,setCategory]=useState('problema'),[status,setStatus]=useState(''),[linked,setLinked]=useState(false),[rating,setRating]=useState(null);
  function open(){trigger.current=document.activeElement;setStatus('');dialog.current.showModal();}
  function close(){if(status==='sending')return;dialog.current.close();trigger.current?.focus();}
  function outsidePanel(event){
    const box=event.currentTarget.getBoundingClientRect();
    return event.clientX<box.left||event.clientX>box.right||event.clientY<box.top||event.clientY>box.bottom;
  }
  function pressBackdrop(event){
    backdropPress.current=event.isPrimary&&event.button===0&&outsidePanel(event)?{x:event.clientX,y:event.clientY}:null;
  }
  function moveBackdrop(event){
    const start=backdropPress.current;
    if(start&&Math.hypot(event.clientX-start.x,event.clientY-start.y)>10)backdropPress.current=null;
  }
  function clickBackdrop(event){
    const start=backdropPress.current;backdropPress.current=null;
    if(!start||!outsidePanel(event))return;
    event.preventDefault();event.stopPropagation();close();
  }
  async function send(e){e.preventDefault();if((!message.trim()&&!rating)||status==='sending')return;setStatus('sending');try{pending.current??=prepareFeedback(category,message.trim(),rating);const result=await submitFeedback(pending.current);setLinked(result.linked);setStatus('sent');setMessage('');setRating(null);pending.current=null;}catch{setStatus('error');}}
  useEffect(()=>{window.addEventListener('pap-open-feedback',open);return()=>window.removeEventListener('pap-open-feedback',open);},[]);
  return <div className="pap-feedback">
    <dialog data-private className="pap-feedback-dialog" ref={dialog} aria-labelledby="feedback-title" onPointerDown={pressBackdrop} onPointerMove={moveBackdrop} onPointerCancel={()=>{backdropPress.current=null;}} onClick={clickBackdrop} onCancel={e=>{e.preventDefault();close();}}>
      <header className="pap-feedback-header"><h2 id="feedback-title">Como foi usar o PaP?</h2><button type="button" className="pap-feedback-close pap-dialog-close" aria-label="Fechar feedback" title="Fechar feedback" disabled={status==='sending'} onClick={close}>×</button></header>
      {status==='sent'?<><p role="status">Obrigado! Seu feedback foi salvo.{linked?' Ele foi relacionado à sessão de pesquisa ativa.':' Nenhuma gravação de navegação foi iniciada.'}</p><button onClick={close}>Concluir</button></>:<form onSubmit={send}><div className="pap-feedback-fields">
        <p>Encontrou um problema ou tem uma sugestão? O envio é voluntário e não inicia gravação de navegação. Se a pesquisa estiver ativa, o relato será vinculado à sessão.</p>
        <fieldset className="pap-rating" disabled={status==='sending'}><legend>Sua avaliação (opcional)</legend>
          <div className="pap-rating-stars">{[1,2,3,4,5].map(value=><label key={value} className={value<=rating?'filled':''}>
            <input type="radio" name="feedback-rating" value={value} checked={rating===value} onChange={()=>{setRating(value);pending.current=null;}} aria-label={`${value} ${value===1?'estrela':'estrelas'}`}/><span aria-hidden="true">★</span>
          </label>)}</div><small>{rating?`${rating} de 5`:'1 = muito ruim · 5 = muito boa'}</small>
          {rating&&<button type="button" onClick={()=>{setRating(null);pending.current=null;}}>Limpar nota</button>}
        </fieldset>
        <label>Tipo<select value={category} disabled={status==='sending'} onChange={e=>{setCategory(e.target.value);pending.current=null;}}><option value="problema">Relatar problema</option><option value="sugestao">Sugerir melhoria</option><option value="elogio">O que funcionou bem</option></select></label>
        <label>Seu feedback{rating?' (opcional)':''}<textarea required={!rating} maxLength={2000} rows={5} value={message} disabled={status==='sending'} onChange={e=>{setMessage(e.target.value);pending.current=null;}} placeholder="Conte o que aconteceu e o que você esperava." /></label>
        <small>{message.length}/2000 · Evite senhas ou dados pessoais.</small>
        </div>{status==='error'&&<p role="alert">Não foi possível salvar. Seu texto foi mantido; tente novamente.</p>}
        <div className="pap-feedback-actions"><button type="button" disabled={status==='sending'} onClick={close}>Voltar</button><button type="submit" disabled={status==='sending'||(!message.trim()&&!rating)}>{status==='sending'?'Enviando…':'Enviar feedback'}</button></div>
      </form>}
    </dialog>
  </div>;
}
