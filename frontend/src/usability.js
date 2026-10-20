let session=null, queue=[], sequence=0, sending=false, generation=0;
const read=key=>{try{return sessionStorage.getItem(key);}catch{return null;}};
const save=(key,value)=>{try{sessionStorage.setItem(key,value);}catch{/* memory only */}};
export function record(type,data){
  if(!session)return;
  sequence+=1;save('pap-usability-seq',String(sequence));
  queue.push({type,data,seq:sequence});if(queue.length>5000){queue.shift();console.warn('PaP: fila de pesquisa excedida; eventos podem ser perdidos.');}
}
export async function startRecording(){
  const current=++generation;
  const response=await fetch('/api/usability/',{headers:{'X-Pap-Session':read('pap-usability-token')||''}});
  if(!response.ok)throw new Error('Registro indisponível.');
  const result=await response.json();
  if(current!==generation)return null;
  sequence=result.session===read('pap-usability-id')?Number(read('pap-usability-seq')||0):0;
  session=result;save('pap-usability-token',result.token);save('pap-usability-id',result.session);
  record('session_start',{width:innerWidth,height:innerHeight});
  trace('device',{schema:1,userAgent:navigator.userAgent,platform:navigator.userAgentData?.platform||navigator.platform,language:navigator.language,languages:navigator.languages,screen:{width:screen.width,height:screen.height,colorDepth:screen.colorDepth},viewport:{width:innerWidth,height:innerHeight},pixelRatio:devicePixelRatio,maxTouchPoints:navigator.maxTouchPoints,timeZone:Intl.DateTimeFormat().resolvedOptions().timeZone});
  return result.session;
}
export function stopRecording(){generation++;session=null;queue=[];}
export async function flush(){
  if(!session||sending||!queue.length)return;
  const active=session,batch=[];let bytes=0;
  while(queue.length&&batch.length<20){const size=new TextEncoder().encode(JSON.stringify(queue[0])).length;if(bytes+size>48000&&batch.length)break;bytes+=size;batch.push(queue.shift());}
  sending=true;
  try{
    const response=await fetch('/api/usability/',{method:'POST',headers:{'Content-Type':'application/json','X-CSRFToken':active.csrf},body:JSON.stringify({token:active.token,events:batch}),keepalive:true});
    if(!response.ok&&session===active&&(response.status>=500||response.status===429))queue.unshift(...batch);
    return response.ok;
  }catch{if(session===active)queue.unshift(...batch);}
  finally{queue=queue.slice(-5000);sending=false;}
}
export async function observedFetch(url,options){
  const start=performance.now();let status=0;
  try{const response=await fetch(url,options);status=response.status;return response;}
  finally{
    const part=String(url).split('?')[0].split('/')[3];
    const endpoint=['board','trips','stops','destination','addresses','walk'].includes(part)?part:'other';
    record('api',{endpoint,status,ms:Math.min(3600000,Math.round(performance.now()-start))});
  }
}
if(typeof window!=='undefined'){
  setInterval(flush,100);
  window.addEventListener('pagehide',flush);
  document.addEventListener('visibilitychange',()=>{if(document.hidden)flush();});
  window.addEventListener('error',()=>record('error',{kind:'uncaught'}));
  window.addEventListener('unhandledrejection',()=>record('error',{kind:'promise'}));
  document.addEventListener('click',event=>{
    const el=event.target.closest?.('button');if(!el)return;
    const target=el.dataset.kind||(
      el.matches('.sp-stop-transparency')?'lamp':el.matches('.sp-route-option')?'route':
      el.matches('.sp-map-cancel')?'cancel':null);
    if(['origin','destination','lamp','route','cancel'].includes(target))record('action',{target});
  },true);
}

export function trace(kind,details){
  if(!session)return;
  const payload=JSON.stringify({kind,at:new Date().toISOString(),elapsed:performance.now(),details});
  if(payload.length<=10000){record('trace',{payload});return;}
  const id=crypto.randomUUID(),total=Math.ceil(payload.length/8000);
  for(let index=0;index<total;index++)record('trace',{payload:JSON.stringify({kind:'chunk',id,index,total,text:payload.slice(index*8000,(index+1)*8000)})});
}
function target(el){
  const parts=[];
  while(el&&el!==document.body){const parent=el.parentElement;parts.unshift(el.tagName.toLowerCase()+':nth-child('+(parent?[...parent.children].indexOf(el)+1:1)+')');el=parent;}
  return parts.join(' > ');
}
if(typeof window!=='undefined'){
  const eligible=el=>el instanceof Element&&!!el.closest('.sp-shell')&&!el.closest('input[type=password]');
  for(const type of ['click','change','input','pointerdown','pointerup','pointercancel'])document.addEventListener(type,e=>{
    if(!eligible(e.target))return;
    trace(type,{target:target(e.target),text:e.target.closest('button')?.textContent,value:'value' in e.target?e.target.value:undefined,x:e.clientX,y:e.clientY,pointer:e.pointerType});
  },true);
  let last=0;
  document.addEventListener('scroll',e=>{if(!eligible(e.target)||performance.now()-last<150)return;last=performance.now();trace('scroll',{target:target(e.target),top:e.target.scrollTop,left:e.target.scrollLeft});},true);
}

export function prepareFeedback(category,message,at,elapsed){
  if(!session)throw new Error('Sessão indisponível. Recarregue a página.');
  sequence+=1;save('pap-usability-seq',String(sequence));
  return {type:'feedback',seq:sequence,data:{payload:JSON.stringify({category,message,at,elapsed})}};
}
export async function submitFeedback(event){
  if(!session)throw new Error('Sessão indisponível.');
  const response=await fetch('/api/usability/',{method:'POST',headers:{'Content-Type':'application/json','X-CSRFToken':session.csrf},body:JSON.stringify({token:session.token,events:[event]})});
  if(!response.ok)throw new Error('Não foi possível salvar. Tente enviar novamente.');
}
