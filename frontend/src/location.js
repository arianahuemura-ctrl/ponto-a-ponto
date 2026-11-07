export function trackLocation(position, navigatorObject, secure, onPosition, onError) {
  if (position) { onPosition(position); return () => {}; }
  if (!secure || !navigatorObject.geolocation) {
    onError('Localização indisponível. No celular, acesse por HTTPS e permita a localização.');
    return () => {};
  }
  const geo = navigatorObject.geolocation;
  const id = geo.watchPosition(({coords}) => onPosition({lat: coords.latitude, lon: coords.longitude, accuracy: coords.accuracy, simulated: false}), error => {
    onPosition(null);
    onError(error.code === 1 ? 'Permissão de localização negada. Você pode continuar escolhendo os pontos no mapa.' : 'Não foi possível atualizar sua localização. Aguardando novo sinal.');
  }, {enableHighAccuracy: true, maximumAge: 0, timeout: 20000});
  return () => geo.clearWatch(id);
}

export function boardingCoordinates(passengerPosition, origin) {
  const point = origin?.useLocation ? passengerPosition || origin.addressCoordinates : origin?.addressCoordinates;
  return point ? {from_lat: point.lat, from_lon: point.lon} : {};
}

export function locationOrigin(position) {
  return {id:'passenger-location',name:'Minha localização',lat:position.lat,lon:position.lon,addressCoordinates:{lat:position.lat,lon:position.lon},useLocation:true};
}

// Encaminhe valores explícitos, inclusive pares vazios/incompletos, para validação no servidor.
export function locationParams(search) {
  const query = new URLSearchParams(search);
  return Object.fromEntries(['location', 'latitude', 'longitude'].filter(key => query.has(key)).map(key => [key, query.get(key)]));
}

export function withLocationParams(path, search) {
  const url = new URL(path, 'http://localhost');
  for (const [key, value] of Object.entries(locationParams(search))) url.searchParams.set(key, value);
  return url.pathname + url.search + url.hash;
}
