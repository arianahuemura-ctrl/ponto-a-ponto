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
      // The URL is authoritative: a bare URL starts a new journey, and
      // a different QR stop must not inherit endpoints from a previous trip.
      if(!stopId||session.origin?.id!==stopId)return {...session,origin:null,destination:null};
    }
    return session;
  } catch { return { origin:null, destination:null }; }
}
export function readFavorites(storage) {
  try { const value=JSON.parse(storage.getItem(favoritesKey)); return Array.isArray(value) ? value.filter(validStop).slice(0,50).map(stop=>{const {favoriteLabel,...point}=stop;return typeof favoriteLabel==='string'&&favoriteLabel.trim()?{...point,favoriteLabel:favoriteLabel.trim().slice(0,80)}:point;}) : []; }
  catch { return []; }
}
export function save(storage,key,value) {
  try { storage.setItem(key,JSON.stringify(value)); return true; } catch { return false; }
}
