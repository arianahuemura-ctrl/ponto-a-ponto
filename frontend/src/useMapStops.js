import {useEffect,useRef,useState} from 'react';
import {api} from './api.js';
import {stopCatalog,preloadStops} from './stopCatalog.js';
const TTL=120000;
const inside=(s,v)=>s.lat>=v.south&&s.lat<=v.north&&s.lon>=v.west&&s.lon<=v.east;
const keyFor=v=>['south','west','north','east','lat','lon'].map(k=>Number(v[k]).toFixed(6)).join(':');

export function useMapStops(viewport) {
  const [stops,setStops]=useState([]),[loading,setLoading]=useState(false),[error,setError]=useState('');
  const cache=useRef(new Map());
  useEffect(()=>{
    if(!viewport)return;
    const abort=new AbortController(),key=keyFor(viewport);
    setError('');setLoading(!stopCatalog.complete);
    const showCatalogue=()=>{
      const visible=[...stopCatalog.stops.values()].filter(s=>inside(s,viewport));
      setStops(visible);setLoading(false);
    };
    if(stopCatalog.complete)showCatalogue();
    const timer=setTimeout(async()=>{
      try {
        // Wait for a whole snapshot; never publish distance-sorted partial pages.
        await preloadStops();
        if(abort.signal.aborted)return;
        if(stopCatalog.complete)showCatalogue();
        const hit=cache.current.get(key);
        if(hit&&Date.now()-hit.time<TTL&&hit.revision===stopCatalog.revision){setStops(hit.stops);return;}
        let offset=0,revision=null;
        const gathered=new Map();
        do {
          const data=await api('sptrans/stops',{...viewport,offset,batch_size:200},abort.signal);
          if(abort.signal.aborted)return;
          if(revision&&data.revision!==revision)throw new Error('O cadastro foi atualizado. Mova o mapa para recarregar.');
          revision=data.revision;
          for(const stop of data.stops)gathered.set(stop.id,stop);
          const next=data.next_offset;
          if(next!=null&&(!Number.isInteger(next)||next<=offset))throw new Error('Não foi possível completar os pontos do mapa.');
          offset=next;
        }while(offset!=null);
        const complete=[...gathered.values()];
        // Apply directions and full precision atomically, keeping all visible points.
        setStops(complete);
        cache.current.set(key,{stops:complete,time:Date.now(),revision});
        while(cache.current.size>8||[...cache.current.values()].reduce((n,c)=>n+c.stops.length,0)>30000)cache.current.delete(cache.current.keys().next().value);
      }catch(e){if(!abort.signal.aborted&&!stopCatalog.complete)setError(e.message);}
      finally{if(!abort.signal.aborted)setLoading(false);}
    },150);
    return()=>{clearTimeout(timer);abort.abort();};
  },[viewport]);
  return {stops,loading,error};
}
