export const stopCatalog={stops:new Map(),revision:null,complete:false};
let pending=null;
async function storage(action,value){
  if(!globalThis.indexedDB)return null;
  return new Promise(resolve=>{
    const request=indexedDB.open('pap-stop-catalogue',1);
    request.onupgradeneeded=()=>request.result.createObjectStore('catalogue');
    request.onerror=()=>resolve(null);request.onblocked=()=>resolve(null);
    request.onsuccess=()=>{
      const db=request.result,tx=db.transaction('catalogue',action==='read'?'readonly':'readwrite');
      const store=tx.objectStore('catalogue');const op=action==='read'?store.get('current'):store.put(value,'current');
      tx.oncomplete=()=>{db.close();resolve(op.result||null);};
      tx.onerror=tx.onabort=()=>{db.close();resolve(null);};
    };
  });
}
export async function decodeCatalogue(data){
  if(data?.version!==1||data.scale!==100000||!Array.isArray(data.rows)||typeof data.revision!=='string')throw new Error('Catálogo inválido');
  const stops=new Map();let lat=0,lon=0,i=0;
  for(const row of data.rows){
    const [id,dy,dx,name]=row;
    if(typeof id!=='string'||!Number.isInteger(dy)||!Number.isInteger(dx)||typeof name!=='string')throw new Error('Ponto inválido');
    lat+=dy;lon+=dx;
    if(Math.abs(lat)>9000000||Math.abs(lon)>18000000)throw new Error('Coordenada inválida');
    stops.set(id,{id,lat:lat/data.scale,lon:lon/data.scale,name});
    if(++i%500===0)await new Promise(resolve=>setTimeout(resolve,0));
  }
  return stops;
}
export function preloadStops(){
  if(pending)return pending;
  pending=(async()=>{
    const cached=await storage('read');let valid=false;
    if(cached)try{stopCatalog.stops=await decodeCatalogue(cached.data);stopCatalog.revision=cached.data.revision;stopCatalog.complete=true;valid=true;}catch{/* Discard invalid stored data. */}
    const response=await fetch('/api/sptrans/stop-catalogue/',{headers:valid?{'If-None-Match':cached.etag}:{}});
    if(response.status===304&&valid)return;
    if(!response.ok)throw new Error('Catálogo indisponível');
    const data=await response.json(),stops=await decodeCatalogue(data);
    stopCatalog.stops=stops;stopCatalog.revision=data.revision;stopCatalog.complete=true;
    await storage('write',{data,etag:response.headers.get('ETag')||`"stops-v1-${data.revision}"`});
  })().catch(()=>{pending=null;});
  return pending;
}
