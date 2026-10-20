import {startVisualRecording,stopVisualRecording} from './visualRecording.js';
import {useState,useEffect} from 'react';
import {startRecording,stopRecording,trace,flush} from './usability.js';
import {preloadStops} from './stopCatalog.js';
export default function UsabilityConsent({children}){
  const [status,setStatus]=useState('ask');
  useEffect(()=>{if(status==='on'){startVisualRecording();return stopVisualRecording;}},[status]);
  const accept=async()=>{
    setStatus('loading');
    try{await startRecording();trace('consent',{version:'research-v4',accepted:true});if(!await flush())throw new Error('Registro indisponível');preloadStops();setStatus('on');}
    catch{stopRecording();setStatus('error');}
  };
  if(status==='on')return children;
  return <main style={{minHeight:'100dvh',boxSizing:'border-box',display:'grid',placeItems:'center',padding:24,background:'#112136',color:'white',fontFamily:'sans-serif'}}>
    <section aria-labelledby="research-title" style={{maxWidth:620,lineHeight:1.6}}>
      <h1 id="research-title">PaP — protótipo em pesquisa</h1>
      <p>Durante esta etapa de desenvolvimento, registramos sua navegação para avaliar a usabilidade e identificar problemas.</p>
      <p>O registro inclui reprodução visual da interface e do mapa, movimentos e toques, ações, telas, buscas digitadas, pontos de origem e destino, localização quando autorizada no navegador, rotas consultadas, falhas e metadados do dispositivo (navegador, idioma e dimensões da tela). Os eventos ficam agrupados por sessão, sem associação a cadastro. Esses dados podem identificar locais e hábitos pessoais; não são anônimos.</p>
      <p>Os registros ficam no servidor do projeto, com acesso local restrito. São mantidos por até 30 dias, com limpeza na próxima gravação. Quando o armazenamento está cheio, novos registros são recusados para preservar os existentes.</p>
      <p>Ao escolher “Concordo e continuar”, você autoriza essa coleta durante a navegação. Se não concordar, feche esta página. Para encerrar a participação, feche o site; isso não apaga os eventos já enviados.</p>
      {status==='error'&&<p role="alert">Não foi possível iniciar o registro. Tente novamente.</p>}
      <button disabled={status==='loading'} onClick={accept} style={{padding:'12px 20px',fontSize:18}}>{status==='loading'?'Iniciando…':'Concordo e continuar'}</button>
    </section>
  </main>;
}
