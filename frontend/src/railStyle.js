// Cor GTFS é a referência; nomes/códigos cobrem sessões antigas sem a cor.
const lines={
  1:['Azul','#0455a1'],2:['Verde','#007e5e'],3:['Vermelha','#ee372f'],
  4:['Amarela','#ffff00'],5:['Lilás','#9b3894'],6:['Laranja','#ff6600'],
  7:['Rubi','#ca016b'],8:['Diamante','#97a098'],9:['Esmeralda','#01a9a7'],
  10:['Turquesa','#049fc3'],11:['Coral','#f68368'],12:['Safira','#133c8d'],
  13:['Jade','#00b352'],15:['Prata','#c0c0c0'],17:['Ouro','#d48500'],
};
export const isRail=line=>line?.mode==='metro'||line?.mode==='rail';
// Long dash + short dot distinguishes rail from buses and pedestrian paths.
export const railDash=past=>past?'6 9 1 9':'12 10 1 10';
export const stationSymbol='<svg class="sp-station-symbol" viewBox="0 0 24 24" aria-hidden="true"><rect x="5" y="3" width="14" height="14" rx="4"/><path d="M5 10h14M8 17l-3 5M16 17l3 5M6 20h12"/><circle cx="8" cy="13" r="1"/><circle cx="16" cy="13" r="1"/></svg>';
const number=line=>{
  for(const value of [line?.route_id,line?.code]){
    const match=String(value||'').match(/^(?:(?:METR[ÔO]|CPTM)\s*)?L?0*(\d+)[AW]?$/i);
    if(match)return Number(match[1]);
  }
  return NaN;
};
export const railNumber=number;
export function railColor(line){
  const color=String(line?.color||'');
  return /^#[\da-f]{6}$/i.test(color)?color:lines[number(line)]?.[1]||'#64748b';
}
// One presentation format shared by maps, route options, legends and accessible names.
export function railLabel(line){
  const n=number(line),name=lines[n]?.[0];
  const metro=line?.mode==='metro'||/^METR[ÔO]/i.test(line?.code||'');
  if(name)return metro?`Metrô Linha ${name}`:`CPTM Linha ${n} ${name}`;
  return line?.code||'Transporte ferroviário';
}
export const railMapLabel=railLabel;
export function railKeys(routes=[]){
  return [...new Map(routes.filter(isRail).map(line=>[railLabel(line),line])).values()];
}
