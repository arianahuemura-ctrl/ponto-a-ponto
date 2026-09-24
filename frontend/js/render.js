function findRouteStopIndex(route, stopKeyValue, fromIndex = 0) {
  const exactIndex = route.orderedStops.indexOf(stopKeyValue, fromIndex);
  if (exactIndex !== -1) return exactIndex;
  const selectedStop = state.stops.get(stopKeyValue);
  if (!selectedStop) return -1;
  if (selectedStop.routeIds.size && !selectedStop.routeIds.has(route.id)) return -1;

  let bestIndex = -1;
  let bestDistance = 35 * 35;
  for (let index = fromIndex; index < route.orderedStops.length; index++) {
    const routeStop = state.stops.get(route.orderedStops[index]);
    if (!routeStop) continue;
    const distance = sqDist([selectedStop.lat, selectedStop.lon], [routeStop.lat, routeStop.lon]);
    if (distance <= bestDistance) {
      bestIndex = index;
      bestDistance = distance;
    }
  }
  return bestIndex;
}

function routeContainsSelectionInOrder(route, ids) {
  if (!ids.length) return true;
  let from = 0;
  for (const wanted of ids) {
    const index = findRouteStopIndex(route, wanted, from);
    if (index === -1) return false;
    from = index + 1
  }
  return true
}

function compatibleRoutesForStop(stop) {
  if (stop.routeIds.size) return new Set(stop.routeIds);
  const routeIds = new Set();
  for (const route of state.routes.values())
    if (findRouteStopIndex(route, stop.key) !== -1) routeIds.add(route.id);
  return routeIds;
}

function computeCompatibleRoutes() {
  state.compatibleRouteIds.clear();
  for (const route of state.routes.values())
    if (routeContainsSelectionInOrder(route, state.selectedStops)) state.compatibleRouteIds.add(route.id)
}

function getPossibleNextStops() {
  const possible = new Set();
  if (!state.selectedStops.length) return possible;
  for (const routeId of state.compatibleRouteIds) {
    const route = state.routes.get(routeId);
    let from = 0;
    for (const selected of state.selectedStops) {
      const index = findRouteStopIndex(route, selected, from);
      if (index < 0) {
        from = route.orderedStops.length;
        break
      }
      from = index + 1
    }
    for (let index = from; index < route.orderedStops.length; index++) {
      const stopKeyValue = route.orderedStops[index];
      const stop = state.stops.get(stopKeyValue);
      if (!stop) continue;
      for (const [key, nearbyStop] of state.stops) {
        if (!nearbyStop.nearby) continue;
        const isSameStop = key === stopKeyValue;
        const isNearbyAlias = sqDist([stop.lat, stop.lon], [nearbyStop.lat, nearbyStop.lon]) <= 35 * 35;
        if ((isSameStop || isNearbyAlias) && (!nearbyStop.routeIds.size || nearbyStop.routeIds.has(routeId))) possible.add(key);
      }
    }
  }
  return possible
}

function buildRouteSegments(route) {
  const segments = route.geometry.filter(segment => segment.length > 1);
  const orientedSegments = [];
  let lastPoint = null;
  for (let index = 0; index < segments.length; index++) {
    let segment = [...segments[index]];
    if (lastPoint) {
      const startDistance = sqDist(lastPoint, segment[0]);
      const endDistance = sqDist(lastPoint, segment[segment.length - 1]);
      if (endDistance < startDistance) segment.reverse();
    }
    orientedSegments.push(segment);
    lastPoint = segment[segment.length - 1]
  }
  return orientedSegments;
}

function buildRoutePoints(route) {
  return buildRouteSegments(route).flat();
}

function getRouteViewportOptions() {
  const isMobile = matchMedia('(max-width:760px)').matches;
  if (!isMobile) {
    return {
      padding: [45, 45],
      minZoom: ROUTE_MIN_ZOOM
    };
  }

  const selectionPanel = $('selection-panel');
  const panelHeight = selectionPanel.hidden ? 0 : selectionPanel.offsetHeight;
  return {
    paddingTopLeft: [20, 90],
    paddingBottomRight: [20, Math.max(150, panelHeight + 105)],
    minZoom: ROUTE_MIN_ZOOM + 1
  };
}

function fitRouteBounds(boundsLayer) {
  const options = getRouteViewportOptions();
  const padding = options.padding || [Math.max(options.paddingTopLeft[0], options.paddingBottomRight[0]), Math.max(options.paddingTopLeft[1], options.paddingBottomRight[1])];
  const fittingZoom = map.getBoundsZoom(boundsLayer, false, L.point(padding[0], padding[1]));
  const targetZoom = Math.min(ROUTE_MAX_ZOOM, Math.max(options.minZoom, fittingZoom));

  if (fittingZoom < options.minZoom) {
    map.setView(boundsLayer.getCenter(), targetZoom, {
      animate: true,
      duration: ROUTE_ANIMATION_DURATION
    });
    if (matchMedia('(max-width:760px)').matches) {
      map.once('zoomend', () => map.panBy([0, -Math.round((options.paddingBottomRight[1] - options.paddingTopLeft[1]) / 3)], {
        animate: true,
        duration: ROUTE_ANIMATION_DURATION
      }));
    }
    return;
  }

  map.fitBounds(boundsLayer, {
    ...options,
    maxZoom: ROUTE_MAX_ZOOM,
    animate: true,
    duration: ROUTE_ANIMATION_DURATION
  });
}

function renderRoutes() {
  layers.routes.clearLayers();
  if (!state.selectedStops.length) return;
  const routeIds = [...state.compatibleRouteIds];
  const lastStop = state.stops.get(state.selectedStops[state.selectedStops.length - 1]);
  const bounds = [];
  for (const routeId of routeIds) {
    const route = state.routes.get(routeId);
    const segments = buildRouteSegments(route);
    const points = segments.flat();
    if (points.length > 1) {
      const selectedSegment = segments.reduce((best, segment, index) => {
        const distance = Math.min(...segment.map(point => sqDist(point, [lastStop.lat, lastStop.lon])));
        return distance < best.distance ? {index, distance} : best;
      }, {index: 0, distance: Infinity}).index;
      const selectedPoints = segments[selectedSegment];
      const split = nearestGeometryIndex(selectedPoints, lastStop);
      const past = selectedPoints.slice(0, split + 1);
      const future = selectedPoints.slice(split);
      for (const [index, segment] of segments.entries()) {
        if (index < selectedSegment && segment.length > 1) L.polyline(segment, {
          color: '#8f9aaa', weight: 5, opacity: .68, dashArray: '8 8'
        }).addTo(layers.routes);
        if (index > selectedSegment && segment.length > 1) L.polyline(segment, {
          color: '#57d68d', weight: 6, opacity: .9
        }).addTo(layers.routes);
      }
      if (past.length > 1) L.polyline(past, {
        color: '#8f9aaa',
        weight: 5,
        opacity: .68,
        dashArray: '8 8'
      }).addTo(layers.routes);
      if (future.length > 1) L.polyline(future, {
        color: '#57d68d',
        weight: 6,
        opacity: .9
      }).addTo(layers.routes);
      bounds.push(...points)
    } else {
      const stopPoints = route.orderedStops.map(key => state.stops.get(key)).filter(Boolean).map(stop => [stop.lat, stop.lon]);
      if (stopPoints.length > 1) {
        const split = nearestGeometryIndex(stopPoints, lastStop);
        const past = stopPoints.slice(0, split + 1);
        const future = stopPoints.slice(split);
        if (past.length > 1) L.polyline(past, {
          color: '#8f9aaa',
          weight: 4,
          opacity: .55,
          dashArray: '6 10'
        }).addTo(layers.routes);
        if (future.length > 1) L.polyline(future, {
          color: '#57d68d',
          weight: 5,
          opacity: .72,
          dashArray: '3 7'
        }).addTo(layers.routes);
        bounds.push(...stopPoints)
      }
    }
  }
  if (bounds.length) {
    const boundsLayer = L.latLngBounds(bounds);
    fitRouteBounds(boundsLayer);
    setTimeout(() => map.invalidateSize(), 120)
  }
  const routeBox = $('routes');
  if (!routeIds.length) {
    routeBox.innerHTML = '<p>Nenhuma linha do OSM passa pelos pontos escolhidos nessa ordem.</p>';
    return
  }
  routeBox.innerHTML = routeIds.map(routeId => {
    const route = state.routes.get(routeId);
    return `<div class="route-item"><div class="route-ref">${esc(routeLabel(route))}</div><div class="route-name">${esc(route.tags.from||'')}${route.tags.to?' → '+esc(route.tags.to):''}${route.tags.operator?' · '+esc(route.tags.operator):''}</div></div>`
  }).join('')
}

function renderSelection() {
  const selectionBox = $('selection');
  if (!state.selectedStops.length) {
    selectionBox.innerHTML = '<p>Nenhum ponto selecionado.</p>';
    return
  }
  selectionBox.innerHTML = state.selectedStops.map((key, index) => `<div>${index+1}. <span class="selected">${esc(stopLabel(state.stops.get(key)))}</span></div>`).join('')
}

function updateMarkerStyles() {
  const possible = getPossibleNextStops();
  for (const [key, marker] of state.markers) {
    if (state.selectedStops.includes(key)) marker.setIcon(makeStopIcon('selected-stop'));
    else if (state.selectedStops.length && possible.has(key)) marker.setIcon(makeStopIcon('available'));
    else marker.setIcon(makeStopIcon());
    const enabled = !state.selectedStops.length || possible.has(key) || state.selectedStops.includes(key);
    marker.getElement()?.style.setProperty('opacity', enabled ? '1' : '.18')
  }
}