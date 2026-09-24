import { useEffect, useRef } from "react";
import L from "leaflet";
import { stopLabel, nearestGeometryIndex, sqDist } from "./utils.js";
function makeStopIcon(className = "") {
  let svgInner;
  if (className.includes("selected-stop"))
    svgInner =
      '<polygon points="12,1 14.9,9.1 23.5,9.3 16.6,14.6 19.1,23 12,17.9 4.9,23 7.4,14.6 0.5,9.3 9.1,9.1" fill="#ffb454" stroke="#000" stroke-width="1.6"/>';
  else if (className.includes("available"))
    svgInner =
      '<rect x="3" y="3" width="18" height="18" rx="3" fill="#57d68d" stroke="#000" stroke-width="2.2"/>';
  else
    svgInner =
      '<polygon points="12,2 22.5,21 1.5,21" fill="#4ea1ff" stroke="#000" stroke-width="2.2" stroke-linejoin="round"/>';
  const html = `<svg width="26" height="26" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" style="filter:drop-shadow(0 1px 2px rgba(0,0,0,.6))">${svgInner}</svg>`;
  return L.divIcon({
    className: "",
    html,
    iconSize: [26, 26],
    iconAnchor: [13, 13],
  });
}

export default function Map({ model, revision, onSelect }) {
  const host = useRef(null),
    mapRef = useRef(null);
  useEffect(() => {
    const map = L.map(host.current).setView([-23.6676, -46.4603], 14);
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).addTo(map);
    mapRef.current = map;
    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);
  useEffect(() => {
    const map = mapRef.current,
      group = L.layerGroup().addTo(map);
    const { state } = model,
      possible = model.getPossibleNextStops();
    if (state.location) {
      const point = [state.location.lat, state.location.lon];
      L.circle(point, {
        radius: 1000,
        color: "#4ea1ff",
        fillOpacity: 0.03,
        weight: 1,
      }).addTo(group);
      L.circleMarker(point, {
        radius: 7,
        color: "#fff",
        fillColor: "#4ea1ff",
        fillOpacity: 1,
      }).addTo(group);
    }
    for (const stop of state.stops.values()) {
      if (!stop.nearby) continue;
      const selected = state.selectedStops.includes(stop.key),
        available = possible.has(stop.key);
      const enabled = !state.selectedStops.length || selected || available;
      const label = document.createElement("span");
      label.textContent = stopLabel(stop);
      L.marker([stop.lat, stop.lon], {
        title: stopLabel(stop),
        alt: stopLabel(stop),
        icon: makeStopIcon(
          selected ? "selected-stop" : available ? "available" : "",
        ),
        opacity: enabled ? 1 : 0.18,
      })
        .bindTooltip(label)
        .on("click", () => {
          if (enabled) onSelect(stop.key);
        })
        .addTo(group);
    }
    const bounds = [];
    const last = state.stops.get(state.selectedStops.at(-1));
    if (last)
      for (const id of state.compatibleRouteIds) {
        const route = state.routes.get(id);
        let segments = model.buildRouteSegments(route),
          approximate = false;
        if (!segments.length) {
          segments = [
            route.orderedStops
              .map((key) => state.stops.get(key))
              .filter(Boolean)
              .map((s) => [s.lat, s.lon]),
          ];
          approximate = true;
        }
        segments = segments.filter((s) => s.length > 1);
        if (!segments.length) continue;
        let selected = 0,
          distance = Infinity;
        segments.forEach((segment, i) =>
          segment.forEach((p) => {
            const d = sqDist(p, [last.lat, last.lon]);
            if (d < distance) {
              distance = d;
              selected = i;
            }
          }),
        );
        const draw = (points, past) => {
          if (points.length > 1)
            L.polyline(points, {
              color: past ? "#8f9aaa" : "#57d68d",
              weight: 5,
              opacity: 0.8,
              dashArray: past ? "8 8" : approximate ? "3 7" : undefined,
            }).addTo(group);
        };
        segments.forEach((segment, i) => {
          if (i === selected) {
            const split = nearestGeometryIndex(segment, last);
            draw(segment.slice(0, split + 1), true);
            draw(segment.slice(split), false);
          } else draw(segment, i < selected);
          bounds.push(...segment);
        });
      }
    if (bounds.length)
      map.fitBounds(bounds, {
        paddingTopLeft: [35, 100],
        paddingBottomRight: matchMedia("(max-width:760px)").matches
          ? [35, 350]
          : [350, 160],
        maxZoom: 15,
      });
    else if (state.location)
      map.setView([state.location.lat, state.location.lon], 15);
    return () => group.remove();
  }, [model, revision, onSelect]);
  return <main id="map" ref={host} aria-label="Mapa dos pontos de ônibus" />;
}
