// Olho Vivo envia HH:mm e o instante ISO da observação. Ancore o relógio
// nessa observação em São Paulo para que a meia-noite nunca transforme
// uma previsão vencida em previsão para amanhã.
export function liveArrivals(arrivals,now=Date.now(),walkingMinutes=0) {
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
    // Mantenha a chegada no minuto atual como zero; remova previsões vencidas.
    if(expected+60000<=now||expected-now>6*3600000)continue;
    if(expected<now+walkingMinutes*60000&&walkingMinutes>0)continue;
    waits.push({...arrival, seconds:Math.max(0,Math.ceil((expected-now)/1000)), expected});
  }
  return waits.sort((a,b)=>a.expected-b.expected);
}

export function boardingMinutes(arrivals,now=Date.now(),walkingMinutes=0) {
  const next=liveArrivals(arrivals,now,walkingMinutes)[0];
  return next?Math.ceil(next.seconds/60):null;
}

export function humanBoarding(seconds) {
  if(seconds<=0)return 'Embarque agora';
  if(seconds<60)return `Embarque em ${Math.ceil(seconds)} s`;
  const minutes=Math.ceil(seconds/60);
  if(minutes<60)return `Embarque em ${minutes} min`;
  const hours=Math.floor(minutes/60),rest=minutes%60;
  return `Embarque em ${hours} h${rest?` ${rest} min`:''}`;
}

// Ordene primeiro uma faixa de frequência ativa e depois o próximo serviço programado datado.
function serviceStart(line,now) {
  return Math.min(...(line.programme||[]).map(p=>{
    const start=Date.parse(p.start),end=Date.parse(p.end);
    if(!Number.isFinite(start))return Infinity;
    if(p.kind==='frequency'&&Number.isFinite(end)&&start<=now&&end>now)return now;
    return start>=now?start:Infinity;
  }));
}

export function orderedBoardLines(lines=[],now=Date.now(),order='arrival') {
  return lines.map(line=>({...line, live:liveArrivals(line.arrivals,now)}))
    .sort((a,b)=>{
      const alphabetical=()=>String(a.headsign||'').localeCompare(String(b.headsign||''),'pt-BR',{sensitivity:'base',numeric:true})||String(a.code||'').localeCompare(String(b.code||''),'pt-BR',{numeric:true});
      if(order==='number')return String(a.code||'').localeCompare(String(b.code||''),'pt-BR',{numeric:true,sensitivity:'base'})||alphabetical();
      if(order==='alphabetical')return alphabetical();
      if(order==='service')return (serviceStart(a,now)-serviceStart(b,now))||alphabetical();
      return (a.live[0]?.expected??Infinity)-(b.live[0]?.expected??Infinity)||(!a.live.length&&!b.live.length?(serviceStart(a,now)-serviceStart(b,now)):0)||alphabetical();
    });
}
