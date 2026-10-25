import './dialogControls.css';
import {useState,useEffect,useRef} from 'react';
import {startVisualRecording,stopVisualRecording} from './visualRecording.js';
import {startRecording,stopRecording,forgetSession,onRecordingStatus} from './usability.js';
import {CHOICE_KEY,readChoice,writeChoice} from './researchChoice.js';
import {availableProofs,researchInfo,researchPost} from './researchApi.js';
import './research.css';

function ResearchDetails(){
  const [info,setInfo]=useState(null),[kind,setKind]=useState('contact'),[message,setMessage]=useState(''),[status,setStatus]=useState(''),[receipt,setReceipt]=useState('');const pending=useRef();
  useEffect(()=>{let live=true;researchInfo().then(x=>{if(live)setInfo(x);}).catch(()=>{});return()=>{live=false;};},[]);
  async function send(e){e.preventDefault();setStatus('sending');try{pending.current??={id:crypto.randomUUID(),kind,message:message.trim(),proofs:kind==='deletion'?availableProofs():[]};const result=await researchPost('requests',pending.current);setReceipt(result.receipt);setStatus('sent');}catch{setStatus('error');}}
  return <section data-private aria-label="Informações da pesquisa"><h3>Dados e finalidade</h3>
    <p>Com sua autorização, registramos reprodução visual da interface e do mapa, movimentos, toques, buscas digitadas, locais de origem e destino, rotas e respostas das consultas, falhas, favoritos e informações técnicas do dispositivo. A localização depende também da permissão do navegador. O objetivo é identificar dificuldades de uso e falhas. Os dados são agrupados por sessão, sem cadastro, mas podem revelar locais e hábitos pessoais: não são anônimos.</p>
    <h3>Acesso, retenção e exclusão</h3><p>Os registros ficam no servidor do projeto, com acesso administrativo restrito. Eventos com mais de 30 dias são removidos quando uma nova gravação é recebida. Sem novas gravações, a remoção pode ocorrer depois desse prazo. Blocos de gravação de sessões ainda existentes, exportações e cópias baixadas podem permanecer e exigem tratamento pelos responsáveis. Não garantimos exclusão de todas as cópias em 30 dias.</p>
    <p>Interromper a participação encerra a captura e descarta eventos ainda não enviados; não apaga automaticamente dados já recebidos. Uma transmissão já recebida pelo servidor não pode ser desfeita pela revogação. Você pode solicitar a exclusão abaixo. A solicitação será analisada pela equipe e não representa exclusão imediata.</p>
    <p>Sem participar, o PaP não inicia gravação de pesquisa. Consultas necessárias ao transporte e logs operacionais do servidor continuam funcionando. Feedback enviado voluntariamente é armazenado separadamente, mesmo sem gravação. Relatos e solicitações são tratados pela equipe, sem limpeza automática por prazo nesta versão.</p>
    <p>Sua decisão é salva neste navegador, separada dos identificadores da gravação. Não há vencimento por prazo nesta versão. Mudanças relevantes na coleta, finalidade, acesso ou retenção exigirão uma nova escolha. Você pode alterar sua participação a qualquer momento nestas configurações.</p>
    <h3>Contato com a equipe</h3>{info?.contact&&<p>{info.contact}</p>}<p>Use este formulário para entrar em contato ou solicitar exclusão. Não informe senhas. Se desejar resposta fora da aplicação, inclua um contato no texto.</p>
    {status==='sent'?<p role="status">Solicitação recebida. Protocolo: {receipt}. Guarde este número.</p>:<form onSubmit={send}>
      <label>Assunto<select aria-label="Assunto" value={kind} onChange={e=>{setKind(e.target.value);pending.current=null;}} disabled={status==='sending'}><option value="contact">Contato sobre a pesquisa</option><option value="deletion">Solicitar exclusão dos registros já enviados</option></select></label>
      {kind==='deletion'&&<p>Serão anexados {availableProofs().length} comprovantes de sessão disponíveis neste navegador (até os 50 mais recentes). Se usou outro aparelho ou apagou o armazenamento, descreva no texto como localizar seus registros. A equipe poderá precisar de mais informações.</p>}
      <label>Mensagem<textarea aria-label="Mensagem" rows={3} maxLength={2000} required value={message} disabled={status==='sending'} onChange={e=>{setMessage(e.target.value);pending.current=null;}}/></label>
      {status==='error'&&<p role="alert">Não foi possível enviar; o texto foi mantido. Tente novamente.</p>}
      <button disabled={status==='sending'||!message.trim()}>{status==='sending'?'Enviando…':'Enviar solicitação'}</button>
    </form>}
  </section>;
}
export default function UsabilityConsent({children}){
  const [choice,setChoice]=useState(readChoice),[phase,setPhase]=useState('off'),[storageWarning,setStorageWarning]=useState(false),[details,setDetails]=useState(false),[settingsOpen,setSettingsOpen]=useState(false);
  const params=new URLSearchParams(location.search);
  const legacy=location.pathname==='/explorar/'||params.get('city')==='maua'||/^(way|node|relation):/.test(params.get('stop')||'');
  const dialog=useRef(),trigger=useRef(),channel=useRef(),backdropPress=useRef(null);
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
    event.preventDefault();event.stopPropagation();dialog.current.close();
  }
  function halt(){stopVisualRecording();stopRecording();forgetSession();}
  function choose(state){
    if(state==='declined')halt();
    const result=writeChoice(state);setStorageWarning(!result.saved);setChoice(result.choice);
    if(state==='declined')channel.current?.postMessage({state:'declined'});
  }
  useEffect(()=>{
    const un=onRecordingStatus(value=>{if(value!=='active')stopVisualRecording();setPhase(value);});return un;
  },[]);
  useEffect(()=>{
    if(choice?.state!=='accepted'){halt();return;}
    let live=true;setPhase('starting');
    startRecording(choice).then(id=>{if(live&&id)startVisualRecording();}).catch(()=>{if(live){stopVisualRecording();stopRecording('unavailable');}});
    return()=>{live=false;stopVisualRecording();stopRecording();};
  },[choice]);
  useEffect(()=>{
    function sync(e){if(e.key!==CHOICE_KEY&&e.key!==null)return;halt();setChoice(readChoice());}
    function open(){trigger.current=document.activeElement;setDetails(false);setSettingsOpen(true);dialog.current?.showModal();}
    window.addEventListener('storage',sync);window.addEventListener('pap-open-research',open);
    try{channel.current=new BroadcastChannel('pap-research-choice');channel.current.onmessage=e=>{if(e.data?.state==='declined'){halt();setChoice({state:'declined',version:'memory-revocation',decidedAt:new Date().toISOString()});}};}catch{/* storage event remains available */}
    return()=>{window.removeEventListener('storage',sync);window.removeEventListener('pap-open-research',open);channel.current?.close();};
  },[]);
  const running=choice?.state==='accepted'&&phase!=='unavailable';
  const recordingSymbol=phase==='active'?'●':phase==='starting'?'◷':phase==='unavailable'?'⚠':'■';
  const recordingLabel=phase==='active'?'Gravação ativa.':phase==='starting'?'Iniciando gravação…':phase==='unavailable'?'Gravação indisponível. Tente novamente.':'Gravação parada.';
  const indicator=<span className={`research-recording-state research-recording-state--${phase}`}><span aria-hidden="true">{recordingSymbol}</span> {recordingLabel}</span>;
  const buttons=<div className="research-choices"><button onClick={()=>choose('accepted')}>Contribuir com a pesquisa</button><button onClick={()=>choose('declined')}>Continuar sem contribuir</button></div>;
  const warning=storageWarning&&<p role="status">Não foi possível salvar sua escolha neste aparelho. Ela vale nesta página; ao recarregar, perguntaremos novamente.</p>;
  return <>
    {!choice?<main className="research-welcome" data-private><section><h1>Ponto a Ponto — Ajude a melhorar o transporte público</h1>
      <p>O PaP é um projeto acadêmico da UNIVESP que facilita a consulta de ônibus e o planejamento de viagens.</p>
      <p>Durante o desenvolvimento, estamos realizando uma pesquisa para identificar dificuldades de navegação e melhorar a experiência dos passageiros.</p>
      <p>Se você optar por contribuir, poderemos registrar suas interações com a aplicação, incluindo movimentos no mapa, buscas, locais consultados e informações técnicas do dispositivo.</p>
      <p>Sua participação é voluntária. Você poderá utilizar todas as funcionalidades do PaP mesmo sem participar da pesquisa.</p>
      <p>Os dados de transporte são fornecidos pela SPTrans. Atualmente, o PaP funciona na cidade de São Paulo.</p>
      {buttons}<button className="research-info-button" onClick={()=>setDetails(x=>!x)} aria-expanded={details}>Informações completas sobre a pesquisa</button>{details&&<ResearchDetails/>}
    </section></main>:<>{children}{legacy&&<button className="research-settings-fallback" data-private onClick={()=>window.dispatchEvent(new Event('pap-open-research'))}>Configurações → Participação na pesquisa</button>}<div className="research-status" data-private role="status">
      {indicator}
      {warning}
    </div></>}
    <dialog onPointerDown={pressBackdrop} onPointerMove={moveBackdrop} onPointerCancel={()=>{backdropPress.current=null;}} onClick={clickBackdrop} className="research-dialog" data-private ref={dialog} aria-labelledby="research-settings-title" onClose={()=>{setSettingsOpen(false);trigger.current?.focus();}}>
      <header><h2 id="research-settings-title">Configurações → Participação na pesquisa</h2><button type="button" className="pap-dialog-close" onClick={()=>dialog.current.close()} aria-label="Fechar configurações" title="Fechar configurações">×</button></header>
      <p>Decisão atual: {choice?.state==='accepted'?'participar':'não participar'}.{choice?.decidedAt&&` Registrada em ${new Date(choice.decidedAt).toLocaleString('pt-BR')}.`}</p>
      <p role="status">{indicator}</p>
      {warning}<div className="research-choices"><button type="button" onClick={()=>choose(running?'declined':'accepted')}><span aria-hidden="true">{running?'■':'●'}</span> {running?'Interromper gravação':'Gravar'}</button></div>
      <p>Interromper não exclui automaticamente os dados já enviados.</p>
      {settingsOpen&&<ResearchDetails/>}
    </dialog>
  </>;
}
