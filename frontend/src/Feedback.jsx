import {useRef,useState,useEffect} from 'react';
import {prepareFeedback,submitFeedback} from './usability.js';
import './feedback.css';
export default function Feedback(){
  const dialog=useRef(),trigger=useRef(),pending=useRef(),moment=useRef();
  const [message,setMessage]=useState(''),[category,setCategory]=useState('problema'),[status,setStatus]=useState('');
  function open(){trigger.current=document.activeElement;moment.current={at:new Date().toISOString(),elapsed:performance.now()};pending.current=null;setStatus('');dialog.current.showModal();}
  function close(){if(status==='sending')return;dialog.current.close();trigger.current?.focus();}
  async function send(e){e.preventDefault();if(!message.trim()||status==='sending')return;setStatus('sending');try{pending.current??=prepareFeedback(category,message.trim(),moment.current.at,moment.current.elapsed);await submitFeedback(pending.current);setStatus('sent');setMessage('');}catch{setStatus('error');}}
  useEffect(()=>{window.addEventListener('pap-open-feedback',open);return()=>window.removeEventListener('pap-open-feedback',open);},[]);
  return <div className="pap-feedback">
    <dialog className="pap-feedback-dialog" ref={dialog} aria-labelledby="feedback-title" onCancel={e=>{if(status==='sending')e.preventDefault();}}>
      <h2 id="feedback-title">Como foi usar o PaP?</h2>
      {status==='sent'?<><p role="status">Obrigado! Seu feedback foi salvo junto à sessão de navegação.</p><button onClick={close}>Concluir</button></>:<form onSubmit={send}>
        <p>Encontrou um problema ou tem uma sugestão? Seu relato será relacionado a este momento da navegação.</p>
        <label>Tipo<select value={category} disabled={status==='sending'} onChange={e=>{setCategory(e.target.value);pending.current=null;}}><option value="problema">Relatar problema</option><option value="sugestao">Sugerir melhoria</option><option value="elogio">O que funcionou bem</option></select></label>
        <label>Seu feedback<textarea required maxLength={2000} rows={5} value={message} disabled={status==='sending'} onChange={e=>{setMessage(e.target.value);pending.current=null;}} placeholder="Conte o que aconteceu e o que você esperava." /></label>
        <small>{message.length}/2000 · Evite senhas ou dados pessoais.</small>
        {status==='error'&&<p role="alert">Não foi possível salvar. Seu texto foi mantido; tente novamente.</p>}
        <div className="pap-feedback-actions"><button type="button" disabled={status==='sending'} onClick={close}>Voltar</button><button type="submit" disabled={status==='sending'||!message.trim()}>{status==='sending'?'Enviando…':'Enviar feedback'}</button></div>
      </form>}
    </dialog>
  </div>;
}
