// Latitude e longitude em graus decimais, separadas por vírgula, ponto e vírgula ou espaço.
export function parseCoordinates(value) {
  const match=value.trim().match(/^([+-]?\d+(?:\.\d+)?)\s*(?:[,;]\s*|\s+)([+-]?\d+(?:\.\d+)?)$/);
  if(!match)return null;
  const lat=Number(match[1]),lon=Number(match[2]);
  if(!Number.isFinite(lat)||!Number.isFinite(lon)||Math.abs(lat)>90||Math.abs(lon)>180)
    return {error:'Coordenadas inválidas. Use latitude entre −90 e 90 e longitude entre −180 e 180.'};
  return {lat,lon};
}
