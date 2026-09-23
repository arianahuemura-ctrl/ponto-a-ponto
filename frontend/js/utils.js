function esc(value=''){return String(value).replace(/[&<>'"]/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','\"':'&quot;'}[char]))}
function routeLabel(route){return route.tags.ref||route.tags.name||`OSM ${route.id}`}
function stopLabel(stop){return stop.tags.name||stop.tags.ref||`Ponto OSM ${stop.id}`}
function wayCenter(geometry=[]){const points=geometry.filter(point=>Number.isFinite(point.lat)&&Number.isFinite(point.lon));if(!points.length)return null;return {lat:points.reduce((sum,point)=>sum+point.lat,0)/points.length,lon:points.reduce((sum,point)=>sum+point.lon,0)/points.length}}
function stopKey(type,id){return `${type}:${id}`}
function sqDist(first,second){const y=(first[0]-second[0])*111320;const x=(first[1]-second[1])*111320*Math.cos((first[0]+second[0])*Math.PI/360);return x*x+y*y}
function nearestGeometryIndex(points,stop){let best=0;let distance=Infinity;for(let index=0;index<points.length;index++){const currentDistance=sqDist(points[index],[stop.lat,stop.lon]);if(currentDistance<distance){distance=currentDistance;best=index}}return best}
