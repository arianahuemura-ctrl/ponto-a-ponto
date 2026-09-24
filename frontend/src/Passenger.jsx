import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Icon from "./Icon.jsx";
import Catalogue from "./Catalogue.jsx";
import PassengerMap from "./PassengerMap.jsx";
import { api, getLocation } from "./api.js";
import { loadPreferences, savePreferences } from "./preferences.js";
const hhmm = (s) => new Date(s * 1000).toISOString().slice(11, 16);
const mins = (s) => Math.max(0, Math.ceil(s / 60));
const allowedViews = new Set([
  "home",
  "lines",
  "destination",
  "filtered",
  "vehicles",
  "detail",
  "favorites",
  "more",
  "catalogue",
]);
export default function Passenger() {
  const [network, setNetwork] = useState(null),
    [origin, setOrigin] = useState(""),
    [destination, setDestination] = useState(null),
    [draft, setDraft] = useState(null);
  const [view, setView] = useState("home"),
    [board, setBoard] = useState({
      at: 28800,
      lines: [],
      vehicles: [],
      mode: null,
    }),
    [journeys, setJourneys] = useState([]);
  const [notice, setNotice] = useState(""),
    [busy, setBusy] = useState(false),
    [tick, setTick] = useState(0);
  const [preferences, setPreferences] = useState(loadPreferences),
    [favoriteName, setFavoriteName] = useState("");
  const [query, setQuery] = useState(""),
    [searching, setSearching] = useState(false),
    [searchResult, setSearchResult] = useState(null);
  const [detail, setDetail] = useState(null),
    [tab, setTab] = useState("times"),
    [pickingOrigin, setPickingOrigin] = useState(false),
    [showQr, setShowQr] = useState(false);
  const [follow, setFollow] = useState(false),
    [notes, setNotes] = useState(""),
    [feedback, setFeedback] = useState("");
  const detailReturn = useRef("lines"),
    searchController = useRef(null),
    scroll = useRef(null);
  const go = useCallback((next) => {
    setView(next);
    history.pushState({ view: next }, "", "#" + next);
  }, []);
  useEffect(() => {
    history.replaceState(
      { view: "home" },
      "",
      location.pathname + location.search,
    );
    const pop = (e) =>
      setView(allowedViews.has(e.state?.view) ? e.state.view : "home");
    window.addEventListener("popstate", pop);
    return () => window.removeEventListener("popstate", pop);
  }, []);
  useEffect(() => {
    scroll.current?.scrollTo(0, 0);
  }, [view, tab]);
  useEffect(() => {
    const controller = new AbortController();
    api("network", {}, controller.signal)
      .then((data) => {
        setNetwork(data);
        setBoard((previous) => ({ ...previous, mode: data.mode, at: data.at }));
        const id = new URLSearchParams(location.search).get("stop");
        const found = data.stops.find((s) => s.id === id);
        setOrigin(found?.id || data.stops.find(s => s.id === data.default_origin)?.id || data.stops[0]?.id || "");
        if (id && !found)
          setNotice("Ponto não encontrado. Selecione outro ponto no mapa.");
      })
      .catch((e) => {
        if (!controller.signal.aborted)
          setNotice(
            "Não foi possível carregar os pontos. Atualize a página para tentar novamente.",
          );
      });
    return () => controller.abort();
  }, []);
  useEffect(() => {
    if (!origin) return;
    let controller;
    const refresh = () => {
      controller?.abort();
      controller = new AbortController();
      const signal = controller.signal;
      api("board", { origin }, signal)
        .then(setBoard)
        .catch(() => {
          if (!signal.aborted)
            setNotice(
              "Não foi possível atualizar as previsões. Tente novamente.",
            );
        });
    };
    refresh();
    const interval = setInterval(refresh, 3000);
    return () => {
      clearInterval(interval);
      controller?.abort();
    };
  }, [origin, tick]);
  useEffect(() => {
    if (!network || !board.mode || network.mode === board.mode) return;
    const controller = new AbortController();
    api("network", {}, controller.signal)
      .then((data) => {
        setNetwork(data);
        if (data.mode !== "simulation") {
          setJourneys([]);
          setDetail(null);
          setFollow(false);
          if (view === "detail") setView("lines");
        }
      })
      .catch(() => {});
    return () => controller.abort();
  }, [board.mode, network, view]);
  const target = view === "destination" ? draft : destination;
  useEffect(() => {
    if (!origin || !target || board.mode !== "simulation") {
      setJourneys([]);
      setBusy(false);
      return;
    }
    const controller = new AbortController();
    setBusy(true);
    setJourneys([]);
    api(
      "journey",
      {
        origin,
        max_transfers: preferences.maxTransfers,
        ...(target.id
          ? { destination: target.id }
          : { lat: target.lat, lon: target.lon }),
      },
      controller.signal,
    )
      .then((data) => {
        setJourneys(data.itineraries);
        setNotice(data.message || "");
      })
      .catch((e) => {
        if (!controller.signal.aborted) setNotice(e.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setBusy(false);
      });
    return () => controller.abort();
  }, [origin, target, board.at, board.mode, preferences.maxTransfers]);
  useEffect(() => () => searchController.current?.abort(), []);
  const routeById = useMemo(
    () => Object.fromEntries((network?.routes || []).map((r) => [r.id, r])),
    [network],
  );
  const stopById = useMemo(
    () => Object.fromEntries((network?.stops || []).map((s) => [s.id, s])),
    [network],
  );
  const stop = stopById[origin];
  const selectedRoute = detail ? routeById[detail.routeId] : null;
  const itinerary = detail?.journey;
  const filteredRows = journeys
    .filter((j) => j.legs.length)
    .map((j) => ({
      route: routeById[j.legs[0].route_id],
      journey: j,
      arrivals: [
        {
          arrival: j.legs[0].departure,
          wait_seconds: j.legs[0].departure - board.at,
        },
      ],
      transfer: j.transfers,
    }));
  const lineRows = board.lines
    .map((l) => ({ route: routeById[l.route_id], arrivals: l.arrivals }))
    .filter((l) => l.route);
  const mapRows = destination ? filteredRows : lineRows;
  const mapSegments = useMemo(() => {
    if (view === "detail" && selectedRoute)
      return itinerary
        ? itinerary.legs.flatMap((leg) =>
            (leg.segments || []).map((s) => ({
              ...s,
              color: routeById[leg.route_id]?.color,
            })),
          )
        : selectedRoute.segments
            .slice(Math.max(0, selectedRoute.stops.indexOf(origin)))
            .map((s) => ({ ...s, color: selectedRoute.color }));
    if (view === "destination")
      return (journeys[0]?.legs || []).flatMap((leg) =>
        (leg.segments || []).map((s) => ({
          ...s,
          color: routeById[leg.route_id]?.color,
        })),
      );
    if (view === "vehicles") {
      const segments = destination
        ? journeys.flatMap((j) =>
            j.legs.flatMap((l) =>
              (l.segments || []).map((s) => ({
                ...s,
                color: routeById[l.route_id]?.color,
              })),
            ),
          )
        : lineRows.flatMap((l) =>
            (l.route.segments || []).map((s) => ({
              ...s,
              color: l.route.color,
            })),
          );
      return [
        ...new Map(segments.map((s) => [s.from + s.to + s.color, s])).values(),
      ];
    }
    return [];
  }, [view, selectedRoute, itinerary, routeById, journeys, destination, board]);
  const vehicleIds = new Set(
    view === "detail" && itinerary
      ? itinerary.legs.map((l) => l.trip_id)
      : destination
        ? journeys.flatMap((j) => j.legs.map((l) => l.trip_id))
        : board.lines.map((l) => l.arrivals[0]?.trip_id),
  );
  const vehicles =
    board.mode === "simulation"
      ? board.vehicles.filter((v) =>
          view === "detail" && !itinerary
            ? v.route_id === detail?.routeId
            : vehicleIds.has(v.id),
        )
      : [];
  const updatePrefs = (value) => {
    setPreferences(value);
    if (!savePreferences(value))
      setNotice(
        "Preferências disponíveis somente nesta sessão: o navegador bloqueou o armazenamento.",
      );
  };
  const selectOrigin = useCallback((id) => {
    setOrigin(id);
    setDestination(null);
    setDraft(null);
    setDetail(null);
    setFollow(false);
    setPickingOrigin(false);
    setNotice("");
    const url = new URL(location.href);
    url.searchParams.set("stop", id);
    url.searchParams.delete("mode");
    history.replaceState({ view: "home" }, "", url.pathname + url.search);
    setView("home");
  }, []);
  const mapStop = useCallback(
    (id) => {
      if (pickingOrigin) {
        selectOrigin(id);
        return;
      }
      if (view === "destination") {
        setDraft(network.stops.find((s) => s.id === id));
        setSearchResult(null);
      } else selectOrigin(id);
    },
    [pickingOrigin, view, network, selectOrigin],
  );
  const mapPlace = useCallback(
    (point) => {
      if (view === "destination" && !pickingOrigin)
        setDraft({
          ...point,
          name: "Local selecionado no mapa",
          address: "Mauá – SP",
        });
    },
    [view, pickingOrigin],
  );
  function pickDestination() {
    setDraft(destination);
    setPickingOrigin(false);
    go("destination");
  }
  function confirmDestination() {
    if (!draft) return;
    setDestination(draft);
    setNotice("");
    go("filtered");
  }
  function openDetail(row) {
    detailReturn.current = view;
    setDetail({ routeId: row.route.id, journey: row.journey || null });
    setTab("times");
    setFollow(false);
    go("detail");
  }
  function saveFavorite() {
    const place = destination || draft;
    if (!place || !favoriteName.trim()) return;
    if (preferences.favorites.length >= 30) {
      setNotice("Remova um favorito antes de adicionar outro.");
      return;
    }
    const id =
      globalThis.crypto?.randomUUID?.() ||
      Date.now().toString(36) + Math.random().toString(36).slice(2);
    updatePrefs({
      ...preferences,
      favorites: [
        ...preferences.favorites,
        {
          id,
          name: favoriteName.trim(),
          lat: place.lat,
          lon: place.lon,
          ...(place.id ? { stopId: place.id } : {}),
        },
      ],
    });
    setFavoriteName("");
    setNotice("Destino salvo nos favoritos.");
  }
  async function findAddress(e) {
    e.preventDefault();
    if (!query.trim()) return;
    searchController.current?.abort();
    const controller = new AbortController();
    searchController.current = controller;
    setSearching(true);
    try {
      const result = await api(
        "geocode",
        { address: query, state: "SP" },
        controller.signal,
      );
      if (!controller.signal.aborted) {
        const place = { ...result, name: query, address: result.label };
        setSearchResult(place);
        setDraft(place);
      }
    } catch (e) {
      if (!controller.signal.aborted) setNotice(e.message);
    } finally {
      if (!controller.signal.aborted) setSearching(false);
    }
  }
  async function locate(asDestination = false) {
    try {
      const point = await getLocation();
      if (asDestination) {
        setDraft({
          ...point,
          name: "Minha localização",
          address: "Localização do dispositivo",
        });
        return;
      }
      const nearest = [...network.stops].sort(
        (a, b) =>
          Math.hypot(a.lat - point.lat, a.lon - point.lon) -
          Math.hypot(b.lat - point.lat, b.lon - point.lon),
      )[0];
      selectOrigin(nearest.id);
    } catch (e) {
      setNotice(e.message);
    }
  }
  async function share() {
    const url = location.origin + "/?stop=" + encodeURIComponent(origin);
    try {
      if (navigator.share)
        await navigator.share({ title: "Meu Ponto · " + stop.code, url });
      else if (navigator.clipboard) {
        await navigator.clipboard.writeText(url);
        setNotice("Link deste ponto copiado.");
      } else {
        setShowQr(true);
        go("more");
      }
    } catch (e) {
      if (e.name !== "AbortError")
        setNotice("Não foi possível compartilhar. Use o QR Code em Mais.");
    }
  }
  async function evaluate(e) {
    e.preventDefault();
    const token = document.cookie
      .split("; ")
      .find((v) => v.startsWith("csrftoken="))
      ?.split("=")[1];
    try {
      const r = await fetch("/api/demo/evaluation/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": token || "",
        },
        body: JSON.stringify({
          notes,
          scenario: stop.code + " · " + hhmm(board.at),
        }),
      });
      if (!r.ok) throw Error();
      setFeedback("Observação registrada.");
      setNotes("");
    } catch {
      setFeedback("Não foi possível registrar. Tente novamente.");
    }
  }
  function summary(compact = false) {
    return (
      <div className={"point-summary " + (compact ? "compact" : "")}>
        <Icon name="pin" />
        <div>
          <small>{destination ? "Origem" : "Ponto " + stop.code}</small>
          {destination && <strong>{stop.code}</strong>}
          <span>{stop.address}</span>
        </div>
        {destination && (
          <>
            <Icon name="swap" size={16} />
            <Icon name="pin" className="red" />
            <div>
              <small>Destino</small>
              <strong>{destination.name.replace(" (demo)", "")}</strong>
              <span>{destination.address || "Local selecionado"}</span>
            </div>
          </>
        )}
        <button
          className="change-point"
          onClick={() => {
            setPickingOrigin(true);
            go("home");
          }}
        >
          <Icon name="swap" size={13} />
          {destination ? "Trocar" : "Trocar ponto"}
        </button>
      </div>
    );
  }
  function row(item, index = 0, compact = false) {
    const { route, arrivals, journey } = item;
    if (!route) return null;
    const first = arrivals[0],
      other = arrivals
        .slice(1)
        .map((a) => mins(a.wait_seconds) + " min")
        .join(", ");
    return (
      <button
        className={"line-card " + (compact ? "small" : "")}
        key={route.id + "-" + index}
        onClick={() => openDetail(item)}
      >
        <span className="line-code" style={{ background: route.color }}>
          {route.code}
        </span>
        <span className="line-text">
          <strong>{route.name.replace(" → ", " ↔ ")}</strong>
          <span className={"arrival " + (destination ? "green" : "")}>
            <Icon name="bus" size={14} />
            {first
              ? (destination ? "Próximo em " : "Chegando em ") +
                mins(first.wait_seconds) +
                " min"
              : "Previsão indisponível"}
          </span>
          <small>
            {journey
              ? mins(journey.duration_seconds) +
                " min até o destino" +
                (journey.transfers
                  ? " · " + journey.transfers + " troca(s)"
                  : " · sem troca")
              : other
                ? "Próximo em " + other
                : "Veja horários e trajeto"}
          </small>
        </span>
        <Icon name="chevron" size={18} />
      </button>
    );
  }
  function map(props = {}) {
    return (
      <PassengerMap
        network={network}
        origin={origin}
        destination={view === "destination" ? draft : destination}
        segments={mapSegments}
        vehicles={view === "vehicles" || view === "detail" ? vehicles : []}
        onStop={mapStop}
        onPlace={mapPlace}
        home={view === "home"}
        focusKey={view + (tab || "") + (detail?.routeId || "")}
        {...props}
      />
    );
  }
  const selectedLine = board.lines.find((l) => l.route_id === detail?.routeId);
  const detailStops = itinerary
    ? itinerary.legs.flatMap((leg, i) => leg.stops.slice(i ? 1 : 0))
    : selectedRoute?.stops.slice(
        Math.max(0, selectedRoute.stops.indexOf(origin)),
      ) || [];
  const detailTime =
    itinerary?.duration_seconds ??
    (selectedLine?.arrivals[0]?.wait_seconds || 0) +
      (selectedRoute?.durations
        .slice(Math.max(0, selectedRoute.stops.indexOf(origin)))
        .reduce((a, b) => a + b, 0) || 0);
  if (!network || !stop)
    return (
      <main className="passenger-shell">
        <header className="passenger-header">
          <span className="brand-mark">
            <Icon name="bus" />
          </span>
          <div>
            <h1>Meu Ponto</h1>
            <p>Transporte público ao seu alcance</p>
          </div>
        </header>
        <div className="loading-screen" role="status">
          {notice || (network ? "Nenhum ponto com coordenadas foi importado ainda." : "Carregando seu ponto…")}
          {network && <Catalogue />}
          {notice && (
            <button className="primary" onClick={() => location.reload()}>
              Tentar novamente
            </button>
          )}
        </div>
      </main>
    );
  return (
    <main className="passenger-shell">
      <header className="passenger-header">
        <button
          className="brand-mark"
          onClick={() => go("home")}
          aria-label="Meu Ponto, início"
        >
          <Icon name="bus" size={28} />
        </button>
        <div>
          <h1>Meu Ponto</h1>
          <p>Transporte público ao seu alcance</p>
        </div>
        <button
          className="icon-button"
          aria-label="Abrir menu"
          onClick={() => go("more")}
        >
          <Icon name="menu" />
        </button>
      </header>
      <div
        className={
          "data-label " + (board.mode !== "simulation" ? "unavailable" : "")
        }
      >
        {board.mode === "simulation"
          ? "Dados simulados · " + hhmm(board.at)
          : "Previsões indisponíveis no momento"}
      </div>
      {notice && (
        <div className="passenger-notice" role="status">
          {notice}
          <button aria-label="Fechar aviso" onClick={() => setNotice("")}>
            <Icon name="close" size={15} />
          </button>
        </div>
      )}
      <div className={"passenger-screen screen-" + view} ref={scroll}>
        {view === "home" && (
          <>
            <div className="home-map-area">
              {map()}
              <button
                className="map-float location-pill"
                onClick={() => locate()}
              >
                <Icon name="locate" size={17} />
                Minha localização
              </button>
              <span className="map-float map-pill">
                <Icon name="map" size={16} />
                Mapa
              </span>
              {pickingOrigin && (
                <div className="map-instruction">
                  Toque em um ponto para definir a origem.
                </div>
              )}
            </div>
            <section className="home-sheet">
              <div className="sheet-heading">
                <div>
                  <h2>Ponto {stop.code}</h2>
                  <p>{stop.address}</p>
                </div>
                <button
                  className="soft-icon"
                  aria-label="Compartilhar ponto"
                  onClick={share}
                >
                  <Icon name="share" />
                </button>
              </div>
              <div className="info-box">
                <span className="brand-mark">
                  <Icon name="bus" size={26} />
                </span>
                <p>
                  Veja as linhas, horários e a posição dos ônibus deste ponto.
                  Toque em um destino para filtrar as opções.
                </p>
              </div>
              <div className="home-actions">
                <button className="primary" onClick={() => go("lines")}>
                  <Icon name="list" />
                  Ver linhas
                  <br />
                  deste ponto
                </button>
                <button className="secondary" onClick={pickDestination}>
                  <Icon name="search" />
                  Buscar destino
                  <br />
                  no mapa
                </button>
              </div>
            </section>
          </>
        )}
        {view === "lines" && (
          <>
            {summary()}
            <section className="screen-content">
              <div className="section-title">
                <div>
                  <h2>Próximos ônibus neste ponto</h2>
                  <button className="text-button" onClick={() => go("catalogue")}>Consultar cadastro de linhas</button>
                  <p>Atualizado às {hhmm(board.at)}</p>
                </div>
                <button
                  className="text-button"
                  onClick={() => {
                    setTick((t) => t + 1);
                    setNotice("");
                  }}
                >
                  <Icon name="refresh" size={14} />
                  Atualizar
                </button>
              </div>
              <div className="line-list">
                {lineRows.map((r, i) => row(r, i))}
              </div>
              {!lineRows.length && (
                <p className="empty-message">
                  Não há previsões disponíveis para este ponto.
                </p>
              )}
              <div className="info-box">
                <Icon name="info" />
                <p>
                  Toque em um destino no mapa para ver apenas as linhas que
                  atendem à origem e ao destino.
                </p>
              </div>
              <button className="primary full" onClick={pickDestination}>
                <Icon name="map" />
                Selecionar destino no mapa
              </button>
              <button
                className="text-button full"
                onClick={() => go("vehicles")}
              >
                Ver ônibus no mapa
              </button>
            </section>
          </>
        )}
        {view === "destination" && (
          <>
            <div className="destination-map-area">
              {map()}
              <form className="map-search" onSubmit={findAddress}>
                <Icon name="search" size={17} />
                <input
                  aria-label="Buscar endereço, ponto ou local"
                  placeholder="Buscar endereço, ponto ou local..."
                  value={query}
                  maxLength={300}
                  onChange={(e) => setQuery(e.target.value)}
                />
                <button aria-label="Buscar destino" disabled={searching}>
                  <Icon name="send" size={16} />
                </button>
              </form>
              <button
                className="map-float gps-destination"
                onClick={() => locate(true)}
              >
                <Icon name="send" size={13} />
                Usar minha localização
              </button>
            </div>
            <section className="destination-sheet">
              <div className="sheet-heading">
                <button
                  className="icon-button"
                  aria-label="Voltar"
                  onClick={() => go("home")}
                >
                  <Icon name="back" size={19} />
                </button>
                <h2>Ponto de destino</h2>
                <button
                  className="icon-button"
                  aria-label="Limpar destino"
                  onClick={() => setDraft(null)}
                >
                  <Icon name="close" size={18} />
                </button>
              </div>
              {draft && (
                <div className="chosen-destination">
                  <Icon name="pin" className="red" />
                  <div>
                    <strong>{draft.name.replace(" (demo)", "")}</strong>
                    <small>{draft.address || "Local escolhido no mapa"}</small>
                  </div>
                </div>
              )}
              <div className="destination-options">
                {[
                  ...(searchResult ? [searchResult] : []),
                  ...network.stops.filter((s) => s.id !== origin),
                ]
                  .filter(
                    (s) =>
                      !query ||
                      s.name.toLowerCase().includes(query.toLowerCase()) ||
                      s === searchResult,
                  )
                  .map((s, i) => (
                    <button
                      key={s.id || i}
                      className={draft?.id && draft.id === s.id ? "chosen" : ""}
                      onClick={() => setDraft(s)}
                    >
                      <Icon name="bus" size={18} />
                      <span>
                        <strong>{s.name.replace(" (demo)", "")}</strong>
                        <small>{s.address}</small>
                      </span>
                      <small>
                        {Math.hypot(
                          (s.lat - stop.lat) * 111,
                          (s.lon - stop.lon) * 102,
                        ).toFixed(1)}{" "}
                        km
                      </small>
                    </button>
                  ))}
              </div>
              <button
                className="primary full"
                disabled={!draft || busy}
                onClick={confirmDestination}
              >
                {busy ? "Calculando opções…" : "Confirmar destino"}
              </button>
            </section>
          </>
        )}
        {view === "filtered" && (
          <>
            {summary(true)}
            <section className="screen-content">
              <h2>Linhas que atendem origem e destino</h2>
              <p className="section-subtitle">
                Opções para chegar ao destino, incluindo trocas quando
                necessárias.
              </p>
              <div className="line-list">
                {filteredRows.map((r, i) => row(r, i))}
              </div>
              {!filteredRows.length && (
                <p className="empty-message">
                  {busy
                    ? "Buscando alternativas…"
                    : "Nenhuma conexão disponível para este destino."}
                </p>
              )}
              <div className="info-box">
                <Icon name="info" />
                <p>
                  Foram encontradas {filteredRows.length} alternativas que
                  atendem à origem e ao destino selecionado.
                </p>
              </div>
              <button className="secondary full" onClick={() => go("vehicles")}>
                <Icon name="map" />
                Ver essas linhas no mapa
                <Icon name="chevron" size={18} />
              </button>
              <button className="text-button full" onClick={pickDestination}>
                Escolher outro destino
              </button>
            </section>
          </>
        )}
        {view === "vehicles" && (
          <>
            {summary(true)}
            <section className="vehicles-heading">
              <h2>
                Veículos em tempo real{" "}
                {board.mode === "simulation" ? "(simulado)" : ""}
              </h2>
              <p>
                Ônibus das linhas que atendem{" "}
                {destination ? "origem e destino" : "este ponto"} no mapa
              </p>
            </section>
            <div className="vehicles-map-area">
              {map()}
              <div className="route-legend">
                {[
                  ...new Set(
                    mapRows.flatMap((r) =>
                      r.journey
                        ? r.journey.legs.map((l) => l.route_id)
                        : [r.route.id],
                    ),
                  ),
                ].map((id) => (
                  <span key={id}>
                    <i style={{ background: routeById[id]?.color }} />
                    Linha {routeById[id]?.code}
                  </span>
                ))}
              </div>
            </div>
            <section className="screen-content vehicle-list">
              <h2>{vehicles.length} ônibus no trajeto</h2>
              <p>Posição aproximada e tempo estimado de chegada no ponto</p>
              {mapRows.map((r, i) => row(r, i, true))}
            </section>
          </>
        )}
        {view === "detail" && !selectedRoute && (
          <section className="screen-content">
            <p>Selecione uma linha para ver seus detalhes.</p>
            <button className="primary full" onClick={() => go("lines")}>
              Ver linhas deste ponto
            </button>
          </section>
        )}
        {view === "detail" && selectedRoute && (
          <>
            <div className="sub-header">
              <button onClick={() => go(detailReturn.current)}>
                <Icon name="back" size={18} />
                Voltar
              </button>
              <h2>
                {tab === "map"
                  ? "Mapa da linha " + selectedRoute.code
                  : itinerary?.transfers
                    ? "Detalhes da viagem"
                    : "Detalhes da linha"}
              </h2>
            </div>
            <section className="detail-heading">
              <span
                className="line-code"
                style={{ background: selectedRoute.color }}
              >
                {selectedRoute.code}
              </span>
              <div>
                <strong>{selectedRoute.name.replace(" → ", " ↔ ")}</strong>
                <p>
                  Via{" "}
                  {selectedRoute.segments
                    .flatMap((s) => s.streets)
                    .filter(Boolean)
                    .slice(0, 3)
                    .join(", ")}
                </p>
              </div>
              <button
                className="text-button favorite-line"
                aria-label={
                  (preferences.routes || []).some(
                    (r) => r.id === selectedRoute.id,
                  )
                    ? "Remover linha dos favoritos"
                    : "Favoritar linha"
                }
                aria-pressed={(preferences.routes || []).some(
                  (r) => r.id === selectedRoute.id,
                )}
                onClick={() => {
                  const saved = preferences.routes || [];
                  updatePrefs({
                    ...preferences,
                    routes: saved.some((r) => r.id === selectedRoute.id)
                      ? saved.filter((r) => r.id !== selectedRoute.id)
                      : [
                          ...saved,
                          {
                            id: selectedRoute.id,
                            name: selectedRoute.name,
                            code: selectedRoute.code,
                          },
                        ],
                  });
                }}
              >
                <Icon name="heart" />
                <small>
                  {(preferences.routes || []).some(
                    (r) => r.id === selectedRoute.id,
                  )
                    ? "Salva"
                    : "Favoritar"}
                </small>
              </button>
            </section>
            {destination && (
              <div className="info-box detail-info">
                <Icon name="bus" />
                <p>
                  Esta opção atende o ponto em que você está ({stop.code}) e
                  segue para {destination.name.replace(" (demo)", "")}.
                  {itinerary?.transfers
                    ? " Inclui " + itinerary.transfers + " troca(s) de ônibus."
                    : ""}
                </p>
              </div>
            )}
            <div
              className="detail-tabs"
              role="tablist"
              aria-label="Detalhes da linha"
            >
              {[
                ["times", "clock", "Horários"],
                ["itinerary", "route", "Itinerário"],
                ["map", "map", "Mapa da linha"],
              ].map(([id, icon, label]) => (
                <button
                  key={id}
                  role="tab"
                  aria-selected={tab === id}
                  onClick={() => setTab(id)}
                >
                  <Icon name={icon} size={16} />
                  {label}
                </button>
              ))}
            </div>
            {tab === "times" && (
              <section className="screen-content">
                <div className="section-title">
                  <Icon name="clock" />
                  <div>
                    <h2>Próximos ônibus neste ponto</h2>
                  <button className="text-button" onClick={() => go("catalogue")}>Consultar cadastro de linhas</button>
                    <p>
                      Previsões{" "}
                      {board.mode === "simulation"
                        ? "em tempo real (simulado)"
                        : "indisponíveis"}
                    </p>
                  </div>
                </div>
                <div className="timetable">
                  {(selectedLine?.arrivals || []).map((a) => (
                    <div key={a.trip_id}>
                      <Icon name="bus" size={20} />
                      <strong>{hhmm(a.arrival)}</strong>
                      <span>
                        <b>Em {mins(a.wait_seconds)} min</b>
                        <small>{destination?.name || a.destination}</small>
                      </span>
                      <Icon name="chevron" size={17} />
                    </div>
                  ))}
                </div>
                <div className="duration-box">
                  <Icon name="clock" size={29} />
                  <div>
                    <span>Tempo estimado até o destino</span>
                    <strong>{mins(detailTime)} min</strong>
                    <small>
                      {itinerary
                        ? mins(itinerary.wait_seconds) +
                          " min de espera · " +
                          itinerary.transfers +
                          " troca(s)"
                        : "Considerando o próximo ônibus"}
                    </small>
                  </div>
                </div>
                <button className="primary full" onClick={() => setTab("map")}>
                  <Icon name="send" />
                  Ver no mapa
                </button>
                {itinerary && (
                  <button
                    className="secondary full"
                    onClick={() => {
                      setFollow((v) => !v);
                      setTab("map");
                    }}
                  >
                    {follow ? "Parar acompanhamento" : "Acompanhar esta viagem"}
                  </button>
                )}
              </section>
            )}
            {tab === "map" && (
              <div className="detail-map-area">
                {map()}
                <div className="map-key">
                  <span>
                    <i className="key-origin" />
                    Ponto de origem ({stop.code})
                  </span>
                  <span>
                    <i className="key-destination" />
                    Ponto de destino
                  </span>
                  <span>
                    <i className="key-road" />
                    Trajeto pelas ruas
                  </span>
                  <span>
                    <Icon name="bus" size={12} />
                    Ônibus (posição simulada)
                  </span>
                </div>
              </div>
            )}
            {(tab === "map" || tab === "itinerary") && (
              <section className="stops-sheet">
                <div className="section-title">
                  <Icon name="bus" />
                  <div>
                    <h2>
                      Paradas{" "}
                      {itinerary?.transfers
                        ? "da viagem"
                        : "da linha " + selectedRoute.code}
                    </h2>
                    <p>
                      {detailStops.length} paradas no total (origem → destino)
                    </p>
                  </div>
                </div>
                {follow && (
                  <div className="info-box">
                    <Icon name="locate" />
                    <p>
                      {board.at >= itinerary.arrival
                        ? "Chegada ao destino."
                        : "Acompanhando os veículos desta viagem."}
                    </p>
                  </div>
                )}
                <ol className="stop-timeline">
                  {detailStops.map((id, i) => (
                    <li
                      key={id + "-" + i}
                      className={
                        i === 0
                          ? "first"
                          : i === detailStops.length - 1
                            ? "last"
                            : ""
                      }
                    >
                      <div>
                        <strong>
                          {i === 0 ? stopById[id]?.code + " – " : ""}
                          {stopById[id]?.name.replace(" (demo)", "")}
                        </strong>
                        <small>
                          {i === 0
                            ? "Ponto de origem (você está aqui)"
                            : i === detailStops.length - 1
                              ? "Destino"
                              : "Parada intermediária"}
                        </small>
                        {itinerary?.legs.some(
                          (l, n) => n > 0 && l.from === id,
                        ) && (
                          <b className="transfer-label">
                            Troque para a linha{" "}
                            {
                              routeById[
                                itinerary.legs.find(
                                  (l, n) => n > 0 && l.from === id,
                                ).route_id
                              ]?.code
                            }
                          </b>
                        )}
                      </div>
                      {i === detailStops.length - 1 && (
                        <small>
                          Chegada em
                          <br />
                          {mins(detailTime)} min
                        </small>
                      )}
                    </li>
                  ))}
                </ol>
                <details className="streets-detail">
                  <summary>Ruas do trajeto</summary>
                  <p>
                    {mapSegments
                      .flatMap((s) => s.streets || [])
                      .filter((s, i, a) => a.indexOf(s) === i)
                      .join(" → ")}
                  </p>
                </details>
              </section>
            )}
          </>
        )}
        {view === "favorites" && (
          <section className="screen-content favorites-screen">
            <h2>Seus favoritos</h2>
            {(preferences.routes || []).map((r) => (
              <div className="favorite-row" key={r.id}>
                <button
                  onClick={() =>
                    routeById[r.id]
                      ? openDetail({ route: routeById[r.id], arrivals: [] })
                      : setNotice("Dados desta linha indisponíveis no momento.")
                  }
                >
                  <Icon name="heart" />
                  <span>
                    Linha {r.code} · {r.name}
                  </span>
                  <Icon name="chevron" size={16} />
                </button>
                <button
                  aria-label={"Remover linha " + r.code}
                  onClick={() =>
                    updatePrefs({
                      ...preferences,
                      routes: preferences.routes.filter((x) => x.id !== r.id),
                    })
                  }
                >
                  <Icon name="close" size={17} />
                </button>
              </div>
            ))}
            <p>Casa, Trabalho ou Escola a um toque de distância.</p>
            {preferences.favorites.map((f) => (
              <div className="favorite-row" key={f.id}>
                <button
                  onClick={() => {
                    setDestination({
                      name: f.name,
                      lat: f.lat,
                      lon: f.lon,
                      ...(f.stopId ? { id: f.stopId } : {}),
                    });
                    go("filtered");
                  }}
                >
                  <Icon name="star" />
                  <span>{f.name === "Casa" ? "Voltar para casa" : f.name}</span>
                  <Icon name="chevron" size={16} />
                </button>
                <button
                  aria-label={"Remover favorito " + f.name}
                  onClick={() =>
                    updatePrefs({
                      ...preferences,
                      favorites: preferences.favorites.filter(
                        (x) => x.id !== f.id,
                      ),
                    })
                  }
                >
                  <Icon name="close" size={17} />
                </button>
              </div>
            ))}
            {!preferences.favorites.length && (
              <div className="info-box">
                <Icon name="star" />
                <p>
                  Escolha um destino no mapa para salvar seu primeiro favorito.
                </p>
              </div>
            )}
            {destination && (
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  saveFavorite();
                }}
              >
                <p>Salvar: {destination.name}</p>
                <label>
                  Nome do favorito
                  <input
                    required
                    maxLength={60}
                    value={favoriteName}
                    placeholder="Casa, Trabalho, Escola"
                    onChange={(e) => setFavoriteName(e.target.value)}
                  />
                </label>
                <button className="primary full">Salvar favorito</button>
              </form>
            )}
            <button className="secondary full" onClick={pickDestination}>
              Escolher destino no mapa
            </button>
            <small className="storage-note">
              Seus favoritos ficam salvos neste navegador.
            </small>
          </section>
        )}
        {view === "catalogue" && <Catalogue />}
        {view === "more" && (
          <section className="screen-content more-screen">
            <h2>Mais</h2>
            <label>
              Preferência de viagem
              <select
                aria-label="Trocas de ônibus"
                value={preferences.maxTransfers}
                onChange={(e) =>
                  updatePrefs({
                    ...preferences,
                    maxTransfers: Number(e.target.value),
                  })
                }
              >
                <option value={0}>Somente viagens diretas</option>
                {[1, 2, 3, 4].map((n) => (
                  <option key={n} value={n}>
                    Até {n} troca(s)
                  </option>
                ))}
              </select>
            </label>
            <button
              className="secondary full"
              onClick={() => setShowQr((v) => !v)}
            >
              <Icon name="share" />
              QR Code deste ponto
            </button>
            {showQr && (
              <article className="qr-poster">
                <header>
                  <Icon name="bus" size={44} />
                  <h2>
                    Transporte
                    <br />
                    Público de Mauá
                  </h2>
                </header>
                <h3>
                  Acesse as informações
                  <br />
                  deste ponto
                </h3>
                <img
                  src={"/api/demo/qr/" + encodeURIComponent(origin) + "/"}
                  alt={"QR Code do ponto " + stop.code}
                />
                <p>
                  Aponte a câmera do seu celular e descubra as linhas, horários
                  e trajetos disponíveis.
                </p>
                <strong>Mobilidade para todos</strong>
                <small>
                  Protótipo acadêmico · dados simulados
                  <br />
                  Sem vínculo ou aprovação oficial da Prefeitura
                </small>
                <button className="primary full" onClick={() => window.print()}>
                  Imprimir sinalização
                </button>
              </article>
            )}
            <details>
              <summary>Sobre os dados</summary>
              <button className="secondary full" onClick={() => go("catalogue")}>Consultar linhas e pontos importados</button>
              <p>{network.disclaimer}</p>
              <p>
                Trajetos calculados sobre ruas do OSM, ainda sem validação
                operacional. Favoritos ficam no navegador.
              </p>
              <a href={network.license_url}>{network.attribution}</a>
            </details>
            <details>
              <summary>Registrar avaliação</summary>
              <form onSubmit={evaluate}>
                <label>
                  Observações
                  <textarea
                    required
                    maxLength={5000}
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                  />
                </label>
                <button className="primary full">Registrar observações</button>
                <p role="status">{feedback}</p>
              </form>
            </details>
          </section>
        )}
      </div>
      <nav className="bottom-nav" aria-label="Navegação principal">
        {[
          ["home", "home", "Início"],
          ["lines", "clock", "Horários"],
          ["favorites", "star", "Favoritos"],
          ["more", "settings", "Mais"],
        ].map(([id, icon, label]) => (
          <button
            key={id}
            className={
              view === id ||
              (id === "home" &&
                ["destination", "filtered", "vehicles", "detail"].includes(
                  view,
                ))
                ? "active"
                : ""
            }
            aria-current={view === id ? "page" : undefined}
            onClick={() => go(id)}
          >
            <Icon name={icon} />
            <span>{label}</span>
          </button>
        ))}
      </nav>
    </main>
  );
}
