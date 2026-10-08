import {retainLive} from './liveRetention.js';
import {useEffect,useState} from 'react';
import {api} from './api.js';

export function useApproachingLines(lines,enabled) {
  const [state,setState]=useState(null);
  const key=JSON.stringify(lines.map(l=>[l.trip_id,l.origin.id]));
  useEffect(()=>{
    setState(null);
    if(!enabled||!lines.length)return;
    const abort=new AbortController();let busy=false;
    const keep=lines.map(()=>retainLive());
    const update=async()=>{
      if(busy||document.hidden)return;
      busy=true;
      try{
        const results=[];
        // Limite a concorrência e não sobreponha rodadas de atualização.
        for(let i=0;i<lines.length&&!abort.signal.aborted;i+=4){
          results.push(...await Promise.all(lines.slice(i,i+4).map(async (line,offset)=>{
            try {const data=await api('sptrans/trips/'+encodeURIComponent(line.trip_id),{origin:line.origin.id,next:1,all:1},abort.signal);return keep[i+offset]({...line,approach:data.approach,approaches:data.approaches,passedApproaches:data.passed_approaches||[]},!!data.approach||!!data.approaches?.length||!!data.passed_approaches?.length);}
            catch{return keep[i+offset]({...line,approach:null,approaches:[],passedApproaches:[]},false);}
          })));
        }
        if(!abort.signal.aborted)setState({key,results});
      }finally{busy=false;}
    };
    update();const timer=setInterval(update,5000);
    document.addEventListener('visibilitychange',update);
    return()=>{abort.abort();clearInterval(timer);document.removeEventListener('visibilitychange',update);};
  },[key,enabled]);
  return enabled&&state?.key===key?state.results:null;
}
