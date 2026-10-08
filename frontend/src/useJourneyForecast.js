import {retainLive} from './liveRetention.js';
import {useEffect,useState} from 'react';
import {api} from './api.js';
import {liveArrivals} from './boardingTime.js';

export function operationalArrival(trip, forecasts, now, accessMinutes=0) {
  let ready=now+accessMinutes*60000;
  for(let index=0;index<trip.legs.length;index++) {
    if(index)ready+=(2+(trip.walks||[]).filter(w=>w.accessType==='transfer'&&w.before_leg===index).reduce((sum,w)=>sum+(Number(w.duration_minutes)||0),0))*60000;
    const prediction=liveArrivals(forecasts[index]?.arrivals,now).find(p=>p.expected>=ready);
    const leg=trip.legs[index];
    const ride=Date.parse(leg.arrival)-Date.parse(leg.departure);
    if(!prediction||!Number.isFinite(ride)||ride<0)return null;
    ready=prediction.expected+ride;
  }
  return ready+(trip.walks||[]).filter(w=>w.accessType==='destination').reduce((sum,w)=>sum+(Number(w.duration_minutes)||0),0)*60000;
}

export function useJourneyForecast(trip,enabled) {
  const [state,setState]=useState(null);
  const key=JSON.stringify(trip.legs.map(l=>[l.trip_id,l.origin.id,l.boarding_index]));
  useEffect(()=>{
    setState(null);
    if(!enabled||trip.legs.length<2)return;
    const abort=new AbortController();let busy=false;
    const keep=trip.legs.map(()=>retainLive());
    const update=async()=>{
      if(busy||document.hidden)return;
      busy=true;
      try {
        await Promise.all(trip.legs.slice(1).map(async(leg,offset)=>{
          let forecast;
          try {
            const data=await api('sptrans/trips/'+encodeURIComponent(leg.trip_id),{origin:leg.origin.id,boarding_index:leg.boarding_index,min_wait_seconds:0},abort.signal);
            forecast={arrivals:data.line?.arrivals||[],error:!!data.warning};
          }catch{forecast={arrivals:[]};}
          if(abort.signal.aborted)return;
          forecast=keep[offset+1](forecast,!!forecast.arrivals.length&&!forecast.error);
          if(!abort.signal.aborted)setState(previous=>({key,values:{...(previous?.key===key?previous.values:{}),[offset+1]:forecast}}));
        }));
      }finally{busy=false;}
    };
    update();const timer=setInterval(update,5000);
    document.addEventListener('visibilitychange',update);
    return()=>{abort.abort();clearInterval(timer);document.removeEventListener('visibilitychange',update);};
  },[key,enabled]);
  return state?.key===key?state.values:{};
}
