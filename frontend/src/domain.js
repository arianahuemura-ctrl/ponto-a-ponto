import { wayCenter, stopKey, sqDist } from "./utils.js";
export function createModel() {
  const state = {
    stops: new Map(),
    routes: new Map(),
    selectedStops: [],
    compatibleRouteIds: new Set(),
    markers: new Map(),
    location: null,
  };
  function normalizeData(data) {
    state.stops.clear();
    state.routes.clear();
    for (const element of data.elements || []) {
      if (
        element.type === "node" &&
        Number.isFinite(element.lat) &&
        Number.isFinite(element.lon)
      ) {
        const isStop =
          element.tags?.highway === "bus_stop" ||
          ["platform", "stop_position"].includes(
            element.tags?.public_transport,
          );
        if (isStop)
          state.stops.set(stopKey("node", element.id), {
            key: stopKey("node", element.id),
            type: "node",
            id: element.id,
            lat: element.lat,
            lon: element.lon,
            tags: element.tags || {},
            routeIds: new Set(),
            nearby: true,
          });
      } else if (
        element.type === "way" &&
        element.tags?.public_transport === "platform" &&
        Array.isArray(element.geometry)
      ) {
        const center = wayCenter(element.geometry);
        if (center)
          state.stops.set(stopKey("way", element.id), {
            key: stopKey("way", element.id),
            type: "way",
            id: element.id,
            lat: center.lat,
            lon: center.lon,
            tags: element.tags || {},
            routeIds: new Set(),
            nearby: true,
          });
      }
    }
    for (const element of data.elements || []) {
      if (element.type !== "relation" || element.tags?.route !== "bus")
        continue;
      const orderedStops = [];
      const geometry = [];
      for (const member of element.members || []) {
        const role = (member.role || "").toLowerCase();
        if (
          (member.type === "node" || member.type === "way") &&
          (role.startsWith("platform") || role.startsWith("stop"))
        ) {
          const key = stopKey(member.type, member.ref);
          let lat = member.lat;
          let lon = member.lon;
          if (
            (!Number.isFinite(lat) || !Number.isFinite(lon)) &&
            Array.isArray(member.geometry)
          ) {
            const center = wayCenter(member.geometry);
            lat = center?.lat;
            lon = center?.lon;
          }
          if (
            !state.stops.has(key) &&
            Number.isFinite(lat) &&
            Number.isFinite(lon)
          )
            state.stops.set(key, {
              key,
              type: member.type,
              id: member.ref,
              lat,
              lon,
              tags: {},
              routeIds: new Set(),
              nearby: false,
            });
          if (state.stops.has(key)) orderedStops.push(key);
        }
        if (member.type === "way" && Array.isArray(member.geometry)) {
          const segment = member.geometry
            .filter(
              (point) =>
                Number.isFinite(point.lat) && Number.isFinite(point.lon),
            )
            .map((point) => [point.lat, point.lon]);
          if (segment.length > 1) geometry.push(segment);
        }
      }
      const route = {
        id: element.id,
        tags: element.tags || {},
        orderedStops,
        geometry,
      };
      state.routes.set(element.id, route);
      for (const key of orderedStops)
        state.stops.get(key)?.routeIds.add(element.id);
    }
    const nearby = [...state.stops.values()].filter((stop) => stop.nearby);
    for (const stop of nearby) {
      if (stop.routeIds.size) continue;
      for (const route of state.routes.values())
        if (
          route.orderedStops.some((key) => {
            const routeStop = state.stops.get(key);
            return (
              routeStop &&
              sqDist([stop.lat, stop.lon], [routeStop.lat, routeStop.lon]) <=
                35 * 35
            );
          })
        )
          stop.routeIds.add(route.id);
    }
  }
  function findRouteStopIndex(route, stopKeyValue, fromIndex = 0) {
    const exactIndex = route.orderedStops.indexOf(stopKeyValue, fromIndex);
    if (exactIndex !== -1) return exactIndex;
    const selectedStop = state.stops.get(stopKeyValue);
    if (!selectedStop) return -1;
    if (selectedStop.routeIds.size && !selectedStop.routeIds.has(route.id))
      return -1;

    let bestIndex = -1;
    let bestDistance = 35 * 35;
    for (let index = fromIndex; index < route.orderedStops.length; index++) {
      const routeStop = state.stops.get(route.orderedStops[index]);
      if (!routeStop) continue;
      const distance = sqDist(
        [selectedStop.lat, selectedStop.lon],
        [routeStop.lat, routeStop.lon],
      );
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
      from = index + 1;
    }
    return true;
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
      if (routeContainsSelectionInOrder(route, state.selectedStops))
        state.compatibleRouteIds.add(route.id);
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
          break;
        }
        from = index + 1;
      }
      for (let index = from; index < route.orderedStops.length; index++) {
        const stopKeyValue = route.orderedStops[index];
        const stop = state.stops.get(stopKeyValue);
        if (!stop) continue;
        for (const [key, nearbyStop] of state.stops) {
          if (!nearbyStop.nearby) continue;
          const isSameStop = key === stopKeyValue;
          const isNearbyAlias =
            sqDist([stop.lat, stop.lon], [nearbyStop.lat, nearbyStop.lon]) <=
            35 * 35;
          if (
            (isSameStop || isNearbyAlias) &&
            (!nearbyStop.routeIds.size || nearbyStop.routeIds.has(routeId))
          )
            possible.add(key);
        }
      }
    }
    return possible;
  }

  function buildRouteSegments(route) {
    const segments = route.geometry.filter((segment) => segment.length > 1);
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
      lastPoint = segment[segment.length - 1];
    }
    return orientedSegments;
  }

  function buildRoutePoints(route) {
    return buildRouteSegments(route).flat();
  }

  return {
    state,
    normalizeData,
    findRouteStopIndex,
    routeContainsSelectionInOrder,
    compatibleRoutesForStop,
    computeCompatibleRoutes,
    getPossibleNextStops,
    buildRouteSegments,
    buildRoutePoints,
  };
}
