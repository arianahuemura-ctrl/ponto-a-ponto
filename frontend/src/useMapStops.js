import {useEffect,useRef,useState} from 'react';
import {api} from './api.js';
const TTL=120000;
const inside=(s,v)=>s.lat>=v.south&&s.lat<=v.north&&s.lon>=v.west&&s.lon<=v.east;
const keyFor=v=>['south','west','north','east','lat','lon'].map(k=>Number(v[k]).toFixed(6)).join(':');

export function useMapStops(viewport) {
  const [stops,setStops]=useState([]),[loading,setLoading]=useState(false),[error,setError]=useState('');
  const cache=useRef(new Map()),known=useRef(new Map()),revision=useRef(null);
  useEffect(()=>{
    if(!viewport)return;
    const abort=new AbortController(),key=keyFor(viewport),now=Date.now();
    const hit=cache.current.get(key);
    setError('');
    if(hit&&now-hit.time<TTL){setStops(hit.stops);setLoading(false);return()=>abort.abort();}
    // Exiba marcadores reutilizáveis imediatamente enquanto completa a nova área visível.
    const reused=[...known.current.values()].filter(s=>now-s.time<TTL&&inside(s.stop,viewport)).map(s=>s.stop);
    setStops(reused);setLoading(true);
    const timer=setTimeout(async()=>{
      let offset=0,gathered=new Map(),activeRevision=null;
      try {
        do {
          const data=await api('sptrans/stops',{...viewport,offset,batch_size:offset===0?32:96},abort.signal);
          if(abort.signal.aborted)return;
          if(activeRevision&&data.revision&&activeRevision!==data.revision)throw new Error('O cadastro foi atualizado durante a consulta. Mova o mapa para recarregar.');
          activeRevision=data.revision||null;
          if(data.revision&&revision.current!==data.revision){cache.current.clear();known.current.clear();revision.current=data.revision;}
          for(const stop of data.stops){gathered.set(stop.id,stop);known.current.delete(stop.id);known.current.set(stop.id,{stop,time:Date.now()});}
          while(known.current.size>8000)known.current.delete(known.current.keys().next().value);
          // Preserve marcadores em cache nas bordas até os novos lotes alcançá-los.
          const visible=new Map([...known.current.values()].filter(s=>Date.now()-s.time<TTL&&inside(s.stop,viewport)).map(s=>[s.stop.id,s.stop]));
          for(const [id,stop] of gathered)visible.set(id,stop);
          setStops([...visible.values()]);
          const next=data.next_offset;
          if(next!=null&&(!Number.isInteger(next)||next<=offset))throw new Error('Não foi possível completar os pontos do mapa.');
          offset=next;
        } while(offset!=null);
        const complete=[...gathered.values()];setStops(complete);
        cache.current.delete(key);cache.current.set(key,{stops:complete,time:Date.now()});
        while(cache.current.size>8||[...cache.current.values()].reduce((n,c)=>n+c.stops.length,0)>30000)cache.current.delete(cache.current.keys().next().value);
      }catch(e){if(!abort.signal.aborted)setError(e.message);}
      finally{if(!abort.signal.aborted)setLoading(false);}
    },150);
    return()=>{clearTimeout(timer);abort.abort();};
  },[viewport]);
  return {stops,loading,error};
}
