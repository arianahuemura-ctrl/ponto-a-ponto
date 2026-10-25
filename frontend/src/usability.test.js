import {test,beforeEach,afterEach} from 'node:test';
import assert from 'node:assert/strict';
import {startRecording,stopRecording,record,trace,flush,isRecording,observedFetch,onRecordingStatus} from './usability.js';
import {NOTICE_VERSION} from './researchChoice.js';
const choice={state:'accepted',version:NOTICE_VERSION,decidedAt:'2026-10-23T12:00:00Z'};
const keys=['window','document','sessionStorage','localStorage','navigator','screen','innerWidth','innerHeight','devicePixelRatio','fetch'];
let originals,hooks,calls;
function storage(){const entries=new Map();return {getItem:key=>entries.get(key)||null,setItem:(key,value)=>entries.set(key,value),removeItem:key=>entries.delete(key)};}
function target(){return {addEventListener:()=>hooks++,removeEventListener:()=>hooks--};}
function ok(data){return {ok:true,status:200,json:async()=>data};}
beforeEach(()=>{
 originals=new Map(keys.map(key=>[key,Object.getOwnPropertyDescriptor(globalThis,key)]));hooks=0;calls=[];
 for(const [key,value] of Object.entries({window:target(),document:target(),sessionStorage:storage(),localStorage:storage(),navigator:{language:'pt-BR'},screen:{width:390,height:844},innerWidth:390,innerHeight:844,devicePixelRatio:1}))Object.defineProperty(globalThis,key,{value,configurable:true,writable:true});
 globalThis.fetch=async(url,options={})=>{calls.push({url,options});return ok(options.method==='POST'?{}:{session:'fake',token:'fake',csrf:'fake'});};
});
afterEach(()=>{stopRecording();for(const [key,descriptor] of originals){if(descriptor)Object.defineProperty(globalThis,key,descriptor);else delete globalThis[key];}});
test('sem consentimento não há listeners, fila transmitida ou sessão',async()=>{
 record('action',{});trace('input',{value:'artificial'});assert.equal(await flush(),false);assert.equal(isRecording(),false);assert.equal(hooks,0);assert.equal(calls.length,0);
 await assert.rejects(startRecording({...choice,state:'declined'}));await assert.rejects(startRecording({...choice,version:'old'}));assert.equal(calls.length,0);
});
test('revogação aborta POST em andamento, remove listeners e descarta fila',async()=>{
 await startRecording(choice);assert.ok(hooks>0);assert.equal(isRecording(),true);
 const first=JSON.parse(calls[1].options.body);assert.equal(JSON.parse(first.events[0].data.payload).kind,'consent');
 let aborted=false;
 globalThis.fetch=(url,{signal})=>new Promise((resolve,reject)=>{signal.addEventListener('abort',()=>{aborted=true;reject(Error('aborted'));});});
 record('action',{});const pending=flush();record('action',{target:'pending'});stopRecording();assert.equal(await pending,false);assert.equal(aborted,true);assert.equal(hooks,0);assert.equal(isRecording(),false);
 globalThis.fetch=()=>{throw Error('Envio após revogação');};record('action',{});trace('input',{});assert.equal(await flush(),false);
});
test('resposta tardia da inicialização não reativa pesquisa após revogação',async()=>{
 let resolve;globalThis.fetch=()=>new Promise(r=>resolve=r);const pending=startRecording(choice);stopRecording();resolve(ok({session:'late',token:'late',csrf:'late'}));assert.equal(await pending,null);assert.equal(isRecording(),false);assert.equal(hooks,0);
});
for(const code of [429,503])test(`falha ${code} encerra captura sem bloquear fetch do transporte`,async()=>{
 await startRecording(choice);const states=[];const unsubscribe=onRecordingStatus(s=>states.push(s));
 globalThis.fetch=async()=>({ok:false,status:code});record('action',{});assert.equal(await flush(),false);assert.equal(isRecording(),false);assert.equal(hooks,0);assert.ok(states.includes('unavailable'));
 globalThis.fetch=async()=>ok({stops:[]});assert.deepEqual(await (await observedFetch('/api/sptrans/stops/')).json(),{stops:[]});assert.equal(await flush(),false);unsubscribe();
});
