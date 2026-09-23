const RealtimeProvider={async fetchVehicles(){return[]}};
let realtimeTimer=null;
let realtimeRefreshInProgress=false;
async function refreshVehicles(){if(realtimeRefreshInProgress)return;realtimeRefreshInProgress=true;try{const vehicles=await RealtimeProvider.fetchVehicles();layers.vehicles.clearLayers();for(const vehicle of vehicles){if(!Number.isFinite(vehicle.lat)||!Number.isFinite(vehicle.lon))continue;const icon=L.divIcon({className:'',html:'<div class="vehicle-icon">🚌</div>',iconSize:[24,24],iconAnchor:[12,12]});L.marker([vehicle.lat,vehicle.lon],{icon}).bindTooltip(vehicle.routeRef?`Linha ${vehicle.routeRef}`:'Ônibus').addTo(layers.vehicles)}}catch(error){console.error('Falha ao atualizar veículos em tempo real.',error)}finally{realtimeRefreshInProgress=false}}
function startRealtimeUpdates(){if(realtimeTimer!==null)return;refreshVehicles();realtimeTimer=setInterval(refreshVehicles,REALTIME_REFRESH_INTERVAL)}
function stopRealtimeUpdates(){if(realtimeTimer===null)return;clearInterval(realtimeTimer);realtimeTimer=null}
