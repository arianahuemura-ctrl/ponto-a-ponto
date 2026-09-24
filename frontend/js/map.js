const map = L.map('map', {
  preferCanvas: true
}).setView(DEFAULT_CENTER, 14);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom: 19,
  attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);
const layers = {
  stops: L.layerGroup().addTo(map),
  routes: L.layerGroup().addTo(map),
  location: L.layerGroup().addTo(map),
  vehicles: L.layerGroup().addTo(map)
};

function makeStopIcon(className = '') {
  let svgInner;
  if (className.includes('selected-stop')) svgInner = '<polygon points="12,1 14.9,9.1 23.5,9.3 16.6,14.6 19.1,23 12,17.9 4.9,23 7.4,14.6 0.5,9.3 9.1,9.1" fill="#ffb454" stroke="#000" stroke-width="1.6"/>';
  else if (className.includes('available')) svgInner = '<rect x="3" y="3" width="18" height="18" rx="3" fill="#57d68d" stroke="#000" stroke-width="2.2"/>';
  else svgInner = '<polygon points="12,2 22.5,21 1.5,21" fill="#4ea1ff" stroke="#000" stroke-width="2.2" stroke-linejoin="round"/>';
  const html = `<svg width="26" height="26" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" style="filter:drop-shadow(0 1px 2px rgba(0,0,0,.6))">${svgInner}</svg>`;
  return L.divIcon({
    className: '',
    html,
    iconSize: [26, 26],
    iconAnchor: [13, 13]
  });
}

function renderAllStops() {
  layers.stops.clearLayers();
  state.markers.clear();
  for (const stop of state.stops.values()) {
    if (!stop.nearby) continue;
    const marker = L.marker([stop.lat, stop.lon], {
      icon: makeStopIcon()
    }).bindTooltip(stopLabel(stop), {
      direction: 'top'
    }).on('click', () => selectStop(stop.key));
    marker.addTo(layers.stops);
    state.markers.set(stop.key, marker)
  }
}