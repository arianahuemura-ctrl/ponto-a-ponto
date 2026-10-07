import {useEffect,useState} from 'react';
import {api} from './api.js';

export function useApproachingBus(leg,enabled=true,walkingMinutes=0,earliestBoarding=null){
  const [result,setResult]=useState(null);
  const trip=leg?.trip_id, origin=leg?.origin?.id, index=leg?.boarding_index;
  const key=trip+':'+origin+':'+index+':'+walkingMinutes+':'+earliestBoarding;
  useEffect(()=>{
    setResult(null);
    if(!enabled||!trip||index==null)return;
    const abort=new AbortController();
    let busy=false;
    const update=async()=>{
      if(busy||document.hidden)return;
      busy=true;
      try{
        const data=await api('sptrans/trips/'+encodeURIComponent(trip),{origin,boarding_index:index,min_wait_seconds:Math.max(walkingMinutes*60,(Date.parse(earliestBoarding)-Date.now())/1000||0,0)},abort.signal);
        if(!abort.signal.aborted)setResult({key,approach:data.approach,arrivals:data.line?.arrivals||[],noReachableArrival:!!data.line?.no_reachable_arrival,error:!!data.warning});
      }catch{if(!abort.signal.aborted)setResult({key,arrivals:[],error:true});}
      finally{busy=false;}
    };
    update();
    const timer=setInterval(update,15000);
    document.addEventListener('visibilitychange',update);
    return()=>{abort.abort();clearInterval(timer);document.removeEventListener('visibilitychange',update);};
  },[trip,origin,index,enabled,key,walkingMinutes,earliestBoarding]);
  return enabled&&result?.key===key?result:null;
}
