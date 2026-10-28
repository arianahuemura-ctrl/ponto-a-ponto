export const sessionKey = 'pap.sp.session';
export const favoritesKey = 'pap.sp.favorites';
export function validStop(stop) {
  return !!stop && typeof stop.id === 'string' && /^\d{1,15}$/.test(stop.id) && typeof stop.name === 'string' && Number.isFinite(stop.lat) && Number.isFinite(stop.lon) && Math.abs(stop.lat)<=90 && Math.abs(stop.lon)<=180;
}
export function readSession(storage, search=null) {
  try {
    const value=JSON.parse(storage.getItem(sessionKey));
    const session = { maxTransfers: Number.isInteger(value?.maxTransfers) && value.maxTransfers>=0 && value.maxTransfers<=3 ? value.maxTransfers : 2, origin: validStop(value?.origin) ? value.origin : null, destination: validStop(value?.destination) ? value.destination : null };
    if(search!==null){
      const stopId=new URLSearchParams(search).get('stop');
      // A URL tem precedência: uma URL sem parâmetros inicia nova viagem, e
      // um QR de outra parada não deve herdar extremidades da viagem anterior.
      if(!stopId||session.origin?.id!==stopId)return {...session,origin:null,destination:null};
      return {...session,destination:null};
    }
    return session;
  } catch { return { origin:null, destination:null }; }
}
export function favoriteStop(stop) {
  if(!stop || typeof stop.name!=='string')return null;
  const label=typeof stop.favoriteLabel==='string'&&stop.favoriteLabel.trim()?{favoriteLabel:stop.favoriteLabel.trim().slice(0,80)}:{};
  // Uma localização favorita é fixa: nunca acompanha futuras atualizações do GPS.
  if(stop.kind==='location'||stop.addressCoordinates||stop.useLocation){
    const point=stop.addressCoordinates||stop;
    if(!Number.isFinite(point.lat)||!Number.isFinite(point.lon)||Math.abs(point.lat)>90||Math.abs(point.lon)>180)return null;
    const {lat,lon}=point;
    const name=typeof stop.destinationAddress==='string'&&stop.destinationAddress.trim()?stop.destinationAddress:stop.name;
    return {kind:'location',id:`location:${lat},${lon}`,name,lat,lon,...label};
  }
  if(!validStop(stop))return null;
  const {id,name,lat,lon}=stop;
  return {id,name,lat,lon,...label};
}
export function readFavorites(storage) {
  try {
    const value=JSON.parse(storage.getItem(favoritesKey));
    if(!Array.isArray(value))return [];
    return [...new Map(value.map(favoriteStop).filter(Boolean).map(s=>[s.id,s])).values()].slice(0,50);
  } catch { return []; }
}
export function save(storage,key,value) {
  try { storage.setItem(key,JSON.stringify(value)); return true; } catch { return false; }
}

// Os atalhos referenciam favoritos existentes; não duplicam os pontos salvos.
export const quickDestinationsKey = 'pap.sp.quickDestinations';
export function readQuickDestinations(storage, favorites) {
  try {
    const value=JSON.parse(storage.getItem(quickDestinationsKey));
    return Object.fromEntries(['home','work'].filter(role=>favorites.some(stop=>stop.id===value?.[role])).map(role=>[role,value[role]]));
  } catch { return {}; }
}
