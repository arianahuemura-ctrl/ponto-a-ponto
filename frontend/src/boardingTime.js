// Olho Vivo sends HH:mm and an ISO observation timestamp. Anchor the clock
// to that observation in São Paulo, so midnight never turns an expired ETA
// into a prediction for tomorrow.
export function boardingMinutes(arrivals,now=Date.now(),walkingMinutes=0) {
  const waits=[];
  for(const arrival of arrivals||[]) {
    if(!/^\d{2}:\d{2}$/.test(arrival.time||''))continue;
    const observed=Date.parse(arrival.observed_at);
    if(!Number.isFinite(observed)||now-observed>300000||observed-now>60000)continue;
    const [h,m]=arrival.time.split(':').map(Number);
    if(h>23||m>59)continue;
    const local=new Date(observed-3*3600000);
    let expected=Date.UTC(local.getUTCFullYear(),local.getUTCMonth(),local.getUTCDate(),h+3,m);
    if(expected-observed < -12*3600000)expected+=86400000;
    if(expected-observed > 12*3600000)expected-=86400000;
    // Keep the current arrival minute as zero; remove expired predictions.
    if(expected+60000<=now||expected-now>6*3600000)continue;
    if(expected<now+walkingMinutes*60000&&walkingMinutes>0)continue;
    waits.push(Math.max(0,Math.ceil((expected-now)/60000)));
  }
  return waits.length?Math.min(...waits):null;
}
