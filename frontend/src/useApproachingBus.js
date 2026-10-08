import {retainLive} from './liveRetention.js';
import {useEffect,useState} from 'react';
import {api} from './api.js';

export function useApproachingBus(leg,enabled=true,walkingMinutes=0,earliestBoarding=null){
  const [result,setResult]=useState(null);
  const trip=leg?.trip_id, origin=leg?.origin?.id, index=leg?.boarding_index, vehicle=leg?.vehicle;
  const key=trip+':'+origin+':'+index+':'+walkingMinutes+':'+earliestBoarding+':'+vehicle;
  useEffect(()=>{
    setResult(null);
    if(!enabled||!trip||(index==null&&!vehicle))return;
    const abort=new AbortController();
    let busy=false;
    const keepPosition=retainLive(),keepForecast=retainLive();
    const publish=data=>{
      const positions=keepPosition({approach:data.approach||null,passedApproaches:data.passed_approaches||[]},!!data.approach||!!data.passed_approaches?.length);
      const forecast=keepForecast({arrivals:data.line?.arrivals||[],noReachableArrival:!!data.line?.no_reachable_arrival,error:!!data.warning},!!data.line?.arrivals?.length&&!data.warning);
      if(!abort.signal.aborted)setResult({key,...positions,...forecast});
    };
    const update=async()=>{
      if(busy||document.hidden)return;
      busy=true;
      try{
        const data=await api('sptrans/trips/'+encodeURIComponent(trip),{origin,...(vehicle?{vehicle}:{boarding_index:index}),min_wait_seconds:Math.max(walkingMinutes*60,(Date.parse(earliestBoarding)-Date.now())/1000||0,0)},abort.signal);
        if(!abort.signal.aborted)publish(data);
      }catch{if(!abort.signal.aborted)publish({warning:true});}
      finally{busy=false;}
    };
    update();
    const timer=setInterval(update,5000);
    document.addEventListener('visibilitychange',update);
    return()=>{abort.abort();clearInterval(timer);document.removeEventListener('visibilitychange',update);};
  },[trip,origin,index,vehicle,enabled,key,walkingMinutes,earliestBoarding]);
  return enabled&&result?.key===key?result:null;
}
