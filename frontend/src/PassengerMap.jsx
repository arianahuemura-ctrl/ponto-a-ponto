import { useEffect, useRef } from "react";
import L from "leaflet";
const bus =
  '<svg viewBox="0 0 24 24" width="19" height="19" fill="none" stroke="currentColor" stroke-width="2"><rect x="5" y="3" width="14" height="16" rx="3"/><path d="M5 11h14M8 19v2m8-2v2M8 15h2m4 0h2"/></svg>';
function pin(color, label) {
  const element = document.createElement("div");
  element.className = "pin-content";
  element.style.background = color;
  element.innerHTML = bus;
  return L.divIcon({
    className: "passenger-pin",
    html: element,
    iconSize: [34, 40],
    iconAnchor: [17, 40],
    tooltipAnchor: [0, -40],
  });
}
export default function PassengerMap({
  network,
  origin,
  destination,
  segments = [],
  vehicles = [],
  onStop,
  onPlace,
  home = false,
  focusKey = "",
  height = "",
}) {
  const host = useRef(),
    ref = useRef(),
    fitKey = useRef(null),
    stopCallback = useRef(onStop),
    placeCallback = useRef(onPlace),
    originPoint = useRef(null);
  originPoint.current = network.stops.find((s) => s.id === origin);
  stopCallback.current = onStop;
  placeCallback.current = onPlace;
  useEffect(() => {
    const map = L.map(host.current, { zoomControl: false }).setView(
      [-23.6676, -46.4603],
      15,
    );
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution:
        '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    }).addTo(map);
    L.control.zoom({ position: "topright" }).addTo(map);
    const centerControl = L.control({ position: "topright" });
    centerControl.onAdd = () => {
      const container = L.DomUtil.create("div", "leaflet-bar center-control");
      const button = L.DomUtil.create("button", "", container);
      button.type = "button";
      button.setAttribute("aria-label", "Centralizar na origem");
      button.innerHTML =
        '<svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="7"/><circle cx="12" cy="12" r="2"/><path d="M12 1v4m0 14v4M1 12h4m14 0h4"/></svg>';
      L.DomEvent.disableClickPropagation(container);
      button.addEventListener("click", () => {
        const point = originPoint.current;
        if (point) map.setView([point.lat, point.lon], 16, { animate: false });
      });
      return container;
    };
    centerControl.addTo(map);
    map.on("click", (e) =>
      placeCallback.current?.({ lat: e.latlng.lat, lon: e.latlng.lng }),
    );
    ref.current = map;
    const observer = new ResizeObserver(() => map.invalidateSize());
    observer.observe(host.current);
    return () => {
      observer.disconnect();
      map.remove();
    };
  }, []);
  useEffect(() => {
    const map = ref.current,
      group = L.layerGroup().addTo(map),
      byId = Object.fromEntries(network.stops.map((s) => [s.id, s]));
    const point = byId[origin];
    for (const stop of network.stops) {
      const isOrigin = stop.id === origin,
        isDestination = stop.id === destination?.id;
      const marker = L.marker([stop.lat, stop.lon], {
        icon:
          isOrigin || isDestination
            ? pin(isDestination ? "#e72532" : "#0065ef")
            : L.divIcon({
                className: "small-stop" + (stop.geolocation?.status === "estimated" ? " estimated-stop" : ""),
                html: bus,
                iconSize: [18, 18],
              }),
        title: stop.name,
        alt: stop.name,
        zIndexOffset: isOrigin || isDestination ? 500 : 0,
      });
      const label = document.createElement("div");
      label.className = "map-stop-label";
      label.textContent = isOrigin
        ? (home ? "Ponto selecionado\n" : "Origem\n") + stop.code
        : isDestination
          ? "Destino selecionado\n" + stop.name.replace(" (demo)", "")
          : stop.name.replace(" (demo)", "");
      if (stop.geolocation?.status === "estimated") label.textContent += " · posição aproximada";
      marker
        .bindTooltip(label, {
          permanent: isOrigin || isDestination,
          direction: "top",
          className: isOrigin ? "origin-tooltip" : "",
          offset: [0, -7],
        })
        .on("click", () => stopCallback.current?.(stop.id))
        .addTo(group);
    }
    if (destination && !destination.id) {
      const text = document.createElement("span");
      text.textContent = destination.name || "Destino selecionado";
      L.marker([destination.lat, destination.lon], { icon: pin("#e72532") })
        .bindTooltip(text, { permanent: true, direction: "top" })
        .addTo(group);
    }
    for (const segment of segments) {
      if (segment.points?.length > 2) {
        L.polyline(segment.points, {
          color: "#fff",
          weight: 8,
          opacity: 0.95,
          interactive: false,
        }).addTo(group);
        L.polyline(segment.points, {
          color: segment.color || "#0065ef",
          weight: 4,
          opacity: 0.95,
          interactive: false,
        }).addTo(group);
      }
    }
    const key =
      origin +
      "|" +
      (destination?.id || destination?.lat || "") +
      "|" +
      focusKey +
      "|" +
      segments.map((s) => s.from + s.to + (s.points?.length || 0)).join(",");
    if (fitKey.current !== key) {
      map.invalidateSize();
      const points = segments.flatMap((s) => s.points || []);
      if (point) points.push([point.lat, point.lon]);
      if (destination) points.push([destination.lat, destination.lon]);
      if (points.length > 1)
        map.fitBounds(points, {
          padding: [48, 55],
          maxZoom: 16,
          animate: false,
        });
      else if (point)
        map.setView([point.lat, point.lon], 16, { animate: false });
      fitKey.current = key;
    }
    return () => group.remove();
  }, [network, origin, destination, segments, home, focusKey]);
  useEffect(() => {
    const group = L.layerGroup().addTo(ref.current);
    // Veículos parados no mesmo local são agrupados, sem deslocar suas coordenadas.
    const groups = new Map();
    for (const vehicle of vehicles) {
      const key = vehicle.lat.toFixed(6) + "," + vehicle.lon.toFixed(6);
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(vehicle);
    }
    for (const list of groups.values()) {
      const first = list[0],
        box = document.createElement("div");
      box.className = "vehicle-content";
      box.style.background = first.color;
      box.innerHTML = bus;
      const code = document.createElement("span");
      code.textContent = list
        .map(
          (v) =>
            network.routes.find((r) => r.id === v.route_id)?.code || v.route_id,
        )
        .join(" / ");
      box.append(code);
      const label = document.createElement("span");
      label.textContent = list
        .map((v) => {
          const route = network.routes.find((r) => r.id === v.route_id);
          return (
            (route?.code || v.route_id) +
            " · " +
            (v.waiting_to_depart ? "aguardando partida" : "em movimento")
          );
        })
        .join(" | ");
      L.marker([first.lat, first.lon], {
        icon: L.divIcon({
          className: "passenger-vehicle",
          html: box,
          iconSize: [36, 40],
        }),
        title: label.textContent,
        zIndexOffset: 1000,
      })
        .bindTooltip(label)
        .addTo(group);
    }
    return () => group.remove();
  }, [network, vehicles]);
  return (
    <div
      className={"passenger-map " + height}
      ref={host}
      aria-label="Mapa dos pontos, ruas do trajeto e ônibus"
    />
  );
}
