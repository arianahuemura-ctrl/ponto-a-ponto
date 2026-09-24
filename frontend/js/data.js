function normalizeData(data) {
  state.stops.clear();
  state.routes.clear();
  for (const element of data.elements || []) {
    if (element.type === 'node' && Number.isFinite(element.lat) && Number.isFinite(element.lon)) {
      const isStop = element.tags?.highway === 'bus_stop' || ['platform', 'stop_position'].includes(element.tags?.public_transport);
      if (isStop) state.stops.set(stopKey('node', element.id), {
        key: stopKey('node', element.id),
        type: 'node',
        id: element.id,
        lat: element.lat,
        lon: element.lon,
        tags: element.tags || {},
        routeIds: new Set(),
        nearby: true
      });
    } else if (element.type === 'way' && element.tags?.public_transport === 'platform' && Array.isArray(element.geometry)) {
      const center = wayCenter(element.geometry);
      if (center) state.stops.set(stopKey('way', element.id), {
        key: stopKey('way', element.id),
        type: 'way',
        id: element.id,
        lat: center.lat,
        lon: center.lon,
        tags: element.tags || {},
        routeIds: new Set(),
        nearby: true
      });
    }
  }
  for (const element of data.elements || []) {
    if (element.type !== 'relation' || element.tags?.route !== 'bus') continue;
    const orderedStops = [];
    const geometry = [];
    for (const member of element.members || []) {
      const role = (member.role || '').toLowerCase();
      if ((member.type === 'node' || member.type === 'way') && (role.startsWith('platform') || role.startsWith('stop'))) {
        const key = stopKey(member.type, member.ref);
        let lat = member.lat;
        let lon = member.lon;
        if ((!Number.isFinite(lat) || !Number.isFinite(lon)) && Array.isArray(member.geometry)) {
          const center = wayCenter(member.geometry);
          lat = center?.lat;
          lon = center?.lon
        }
        if (!state.stops.has(key) && Number.isFinite(lat) && Number.isFinite(lon)) state.stops.set(key, {
          key,
          type: member.type,
          id: member.ref,
          lat,
          lon,
          tags: {},
          routeIds: new Set(),
          nearby: false
        });
        if (state.stops.has(key)) orderedStops.push(key);
      }
      if (member.type === 'way' && Array.isArray(member.geometry)) {
        const segment = member.geometry.filter(point => Number.isFinite(point.lat) && Number.isFinite(point.lon)).map(point => [point.lat, point.lon]);
        if (segment.length > 1) geometry.push(segment)
      }
    }
    const route = {
      id: element.id,
      tags: element.tags || {},
      orderedStops,
      geometry
    };
    state.routes.set(element.id, route);
    for (const key of orderedStops) state.stops.get(key)?.routeIds.add(element.id);
  }
  const nearby = [...state.stops.values()].filter(stop => stop.nearby);
  for (const stop of nearby) {
    if (stop.routeIds.size) continue;
    for (const route of state.routes.values())
      if (route.orderedStops.some(key => {
          const routeStop = state.stops.get(key);
          return routeStop && sqDist([stop.lat, stop.lon], [routeStop.lat, routeStop.lon]) <= 35 * 35
        })) stop.routeIds.add(route.id);
  }
}