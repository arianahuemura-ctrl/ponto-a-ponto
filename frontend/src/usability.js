import {NOTICE_VERSION,validChoice} from './researchChoice.js';
import {rememberProof,researchPost} from './researchApi.js';
let session=null,queue=[],sequence=0,generation=0,allowed=false,timer=null;
const controllers=new Set(),listeners=new Set(),cleanup=[];
let sending=null;
const read=key=>{try{return sessionStorage.getItem(key);}catch{return null;}};
const save=(key,value)=>{try{sessionStorage.setItem(key,value);}catch{/* memory only */}};
export const isRecording=()=>allowed&&!!session;
export const onRecordingStatus=fn=>{listeners.add(fn);return()=>listeners.delete(fn);};
function status(value){for(const fn of listeners)fn(value);}
export function record(type,data){
  if(!isRecording())return;
  sequence++;save('pap-usability-seq',String(sequence));queue.push({type,data,seq:sequence});
  if(queue.length>5000)queue.shift();
}
function listen(target,name,fn,capture=false){target.addEventListener(name,fn,capture);cleanup.push(()=>target.removeEventListener(name,fn,capture));}
function target(el){const parts=[];while(el&&el!==document.body){const parent=el.parentElement;parts.unshift(el.tagName.toLowerCase()+':nth-child('+(parent?[...parent.children].indexOf(el)+1:1)+')');el=parent;}return parts.join(' > ');}
function attach(){
  timer=setInterval(flush,100);
  listen(window,'pagehide',flush);
  listen(document,'visibilitychange',()=>{if(document.hidden)flush();});
  listen(window,'error',()=>record('error',{kind:'uncaught'}));
  listen(window,'unhandledrejection',()=>record('error',{kind:'promise'}));
  listen(document,'click',event=>{
    if(event.target.closest?.('[data-private]'))return;
    const el=event.target.closest?.('button');if(!el)return;
    const action=el.dataset.kind||(el.matches('.sp-stop-transparency')?'lamp':el.matches('.sp-route-option')?'route':el.matches('.sp-map-cancel')?'cancel':null);
    if(['origin','destination','lamp','route','cancel'].includes(action))record('action',{target:action});
  },true);
  const eligible=el=>el instanceof Element&&!!el.closest('.sp-shell')&&!el.closest('[data-private],input[type=password]');
  for(const type of ['click','change','input','pointerdown','pointerup','pointercancel'])listen(document,type,e=>{
    if(!isRecording()||!eligible(e.target))return;
    trace(type,{target:target(e.target),text:e.target.closest('button')?.textContent,value:'value' in e.target?e.target.value:undefined,x:e.clientX,y:e.clientY,pointer:e.pointerType});
  },true);
  let last=0;listen(document,'scroll',e=>{if(!isRecording()||!eligible(e.target)||performance.now()-last<150)return;last=performance.now();trace('scroll',{target:target(e.target),top:e.target.scrollTop,left:e.target.scrollLeft});},true);
}
export async function startRecording(choice){
  if(!validChoice(choice)||choice.state!=='accepted')throw Error('Consentimento necessário.');
  stopRecording();allowed=true;const current=generation;const controller=new AbortController();controllers.add(controller);
  const timeout=setTimeout(()=>controller.abort(),8000);
  try{
    const response=await fetch('/api/usability/',{headers:{'X-Pap-Session':read('pap-usability-token')||''},signal:controller.signal});
    if(!response.ok)throw Error('Registro indisponível.');
    const result=await response.json();
    if(current!==generation||!allowed)return null;
    if(!result.session||!result.token||!result.csrf)throw Error('Registro inválido.');
    sequence=result.session===read('pap-usability-id')?Number(read('pap-usability-seq')||0):0;
    session=result;save('pap-usability-token',result.token);save('pap-usability-id',result.session);rememberProof(result.deletion_proof);
    trace('consent',{version:NOTICE_VERSION,accepted:true,decidedAt:choice.decidedAt});
    record('session_start',{width:innerWidth,height:innerHeight});
    trace('device',{schema:1,userAgent:navigator.userAgent,platform:navigator.userAgentData?.platform||navigator.platform,language:navigator.language,languages:navigator.languages,screen:{width:screen.width,height:screen.height,colorDepth:screen.colorDepth},viewport:{width:innerWidth,height:innerHeight},pixelRatio:devicePixelRatio,maxTouchPoints:navigator.maxTouchPoints,timeZone:Intl.DateTimeFormat().resolvedOptions().timeZone});
    if(!await flush())throw Error('Registro indisponível.');
    if(current!==generation||!isRecording())return null;
    attach();status('active');return result.session;
  }catch(error){if(current===generation)stopRecording('unavailable');throw error;}
  finally{clearTimeout(timeout);controllers.delete(controller);}
}
export function stopRecording(reason='off'){
  generation++;allowed=false;session=null;queue=[];sending=null;
  if(timer)clearInterval(timer);timer=null;while(cleanup.length)cleanup.pop()();
  for(const c of controllers)c.abort();controllers.clear();status(reason);
}
export function forgetSession(){for(const k of ['pap-usability-token','pap-usability-id','pap-usability-seq'])try{sessionStorage.removeItem(k);}catch{/* unavailable */}}
export async function flush(){
  if(!isRecording()||sending||!queue.length)return false;
  const active=session,current=generation,batch=[];let bytes=0;
  while(queue.length&&batch.length<20){const size=new TextEncoder().encode(JSON.stringify(queue[0])).length;if(bytes+size>48000&&batch.length)break;bytes+=size;batch.push(queue.shift());}
  const controller=new AbortController();controllers.add(controller);sending=controller;const timeout=setTimeout(()=>controller.abort(),8000);
  try{
    const response=await fetch('/api/usability/',{method:'POST',headers:{'Content-Type':'application/json','X-CSRFToken':active.csrf},body:JSON.stringify({token:active.token,events:batch}),signal:controller.signal});
    if(current!==generation)return false;
    if(!response.ok){stopRecording('unavailable');return false;}return true;
  }catch{if(current===generation)stopRecording('unavailable');return false;}
  finally{clearTimeout(timeout);controllers.delete(controller);if(sending===controller)sending=null;}
}
export async function observedFetch(url,options){const start=performance.now();let code=0;try{const r=await fetch(url,options);code=r.status;return r;}finally{if(isRecording()){const part=String(url).split('?')[0].split('/')[3];record('api',{endpoint:['board','trips','stops','destination','addresses','walk'].includes(part)?part:'other',status:code,ms:Math.min(3600000,Math.round(performance.now()-start))});}}}
export function trace(kind,details){
  if(!isRecording())return;
  const payload=JSON.stringify({kind,at:new Date().toISOString(),elapsed:performance.now(),details});
  if(payload.length<=10000){record('trace',{payload});return;}
  const id=crypto.randomUUID(),total=Math.ceil(payload.length/8000);
  for(let index=0;index<total;index++)record('trace',{payload:JSON.stringify({kind:'chunk',id,index,total,text:payload.slice(index*8000,(index+1)*8000)})});
}
export function prepareFeedback(category,message){return {id:crypto.randomUUID(),category,message};}
export function submitFeedback(event){return researchPost('feedback',{...event,...(isRecording()?{token:session.token}:{})});}
