import { useCallback, useEffect, useRef, useState } from "react";
import Map from "./Map.jsx";
import { createModel } from "./domain.js";
import { routeLabel, stopLabel } from "./utils.js";
import { api, getLocation } from "./api.js";

const states =
  "AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO".split(
    " ",
  );
function Legend() {
  return (
    <div className="legend">
      <div>
        <span className="legend-symbol legend-symbol--nearby">▲</span>Triângulo
        — ponto próximo
      </div>
      <div>
        <span className="legend-symbol legend-symbol--available">■</span>
        Quadrado — destino possível
      </div>
      <div>
        <span className="legend-symbol legend-symbol--selected">★</span>Estrela
        — ponto selecionado
      </div>
      <div>
        <span className="legend-line" />
        Trecho após o ponto selecionado
      </div>
      <div>
        <span className="legend-line legend-line--past" />
        Trecho anterior ao ponto selecionado
      </div>
    </div>
  );
}
export default function Explorer() {
  const [model, setModel] = useState(createModel),
    [revision, setRevision] = useState(0);
  const [address, setAddress] = useState(""),
    [uf, setUf] = useState("SP");
  const [status, setStatus] = useState(
      "Informe um endereço ou use sua localização.",
    ),
    [busy, setBusy] = useState(false);
  const [legend, setLegend] = useState(false);
  const request = useRef(null),
    toggle = useRef(null),
    close = useRef(null);
  const { state } = model;
  const refresh = useCallback(() => setRevision((v) => v + 1), []);
  const reset = useCallback(() => {
    model.state.selectedStops = [];
    model.state.compatibleRouteIds.clear();
    refresh();
  }, [model, refresh]);
  const undo = useCallback(() => {
    model.state.selectedStops.pop();
    if (model.state.selectedStops.length) model.computeCompatibleRoutes();
    else model.state.compatibleRouteIds.clear();
    refresh();
  }, [model, refresh]);
  const select = useCallback(
    (key) => {
      const s = model.state;
      if (s.selectedStops.includes(key)) return;
      if (s.selectedStops.length && !model.getPossibleNextStops().has(key))
        return;
      s.selectedStops.push(key);
      model.computeCompatibleRoutes();
      refresh();
    },
    [model, refresh],
  );
  useEffect(() => () => request.current?.abort(), []);
  useEffect(() => {
    const handler = (e) => {
      if (
        legend ||
        e.target.closest('input,select,textarea,[contenteditable="true"]')
      )
        return;
      if (e.key === "Escape") reset();
      if (e.key === "Backspace" || e.key === "Delete") {
        e.preventDefault();
        undo();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [legend, reset, undo]);
  useEffect(() => {
    if (!legend) return;
    close.current?.focus();
    const pop = () => {
      setLegend(false);
      toggle.current?.focus();
    };
    const key = (e) => {
      if (e.key === "Escape") {
        e.preventDefault();
        history.back();
      }
      if (e.key === "Tab") {
        e.preventDefault();
        close.current?.focus();
      }
    };
    window.addEventListener("popstate", pop);
    window.addEventListener("keydown", key);
    return () => {
      window.removeEventListener("popstate", pop);
      window.removeEventListener("keydown", key);
    };
  }, [legend]);
  async function load(useGps = false) {
    request.current?.abort();
    const controller = new AbortController();
    request.current = controller;
    setBusy(true);
    setStatus(useGps ? "Obtendo localização…" : "Buscando endereço…");
    try {
      const location = useGps
        ? await getLocation()
        : await api(
            "geocode",
            { address: address.trim(), state: uf },
            controller.signal,
          );
      if (controller.signal.aborted) return;
      setStatus("Consultando pontos e linhas no OpenStreetMap…");
      const data = await api(
        "nearby",
        { lat: location.lat, lon: location.lon },
        controller.signal,
      );
      if (controller.signal.aborted) return;
      const next = createModel();
      next.normalizeData(data);
      next.state.location = location;
      setModel(next);
      const count = [...next.state.stops.values()].filter(
        (s) => s.nearby,
      ).length;
      setStatus(
        count
          ? count +
              " pontos próximos · " +
              next.state.routes.size +
              " linhas mapeadas. Selecione um ponto."
          : "Nenhum ponto mapeado nesta área. Tente outro endereço.",
      );
    } catch (error) {
      if (!controller.signal.aborted) setStatus(error.message);
    } finally {
      if (request.current === controller) setBusy(false);
    }
  }
  return (
    <div id="app">
      <Map model={model} revision={revision} onSelect={select} />
      <div className="notice" role="status" aria-live="polite">
        {status}
        <small>
          Dados do OSM · sem posições de veículos ou previsões de chegada nesta
          versão.
        </small>
      </div>
      <section
        className="floating-panel legend-panel"
        aria-label="Legenda do mapa"
      >
        <h1>Ônibus próximos</h1>
        <Legend />
      </section>
      <button
        ref={toggle}
        className="legend-button"
        aria-label="Abrir legenda"
        aria-expanded={legend}
        onClick={() => {
          history.pushState({ mbmLegend: true }, "", "#legenda");
          setLegend(true);
        }}
      >
        i
      </button>
      {legend && (
        <div className="legend-modal">
          <div
            className="legend-modal-backdrop"
            onClick={() => history.back()}
          />
          <section
            className="legend-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="legend-title"
          >
            <div className="legend-dialog-header">
              <h2 id="legend-title">Legenda do mapa</h2>
              <button
                ref={close}
                className="icon-button"
                aria-label="Fechar legenda"
                onClick={() => history.back()}
              >
                ×
              </button>
            </div>
            <Legend />
          </section>
        </div>
      )}
      {!!state.selectedStops.length && (
        <section
          id="selection-panel"
          className="floating-panel selection-panel"
          aria-label="Seleção atual"
        >
          <div className="panel-heading">
            <span>Seleção</span>
            <button
              className="icon-button"
              aria-label="Limpar seleção"
              onClick={reset}
            >
              ×
            </button>
          </div>
          <div id="selection">
            {state.selectedStops.map((key, i) => (
              <div key={key}>
                {i + 1}.{" "}
                <span className="selected">
                  {stopLabel(state.stops.get(key))}
                </span>
              </div>
            ))}
          </div>
          <button onClick={undo}>Desfazer último ponto</button>
          <div className="routes-heading">Linhas compatíveis</div>
          <div id="routes">
            {[...state.compatibleRouteIds].map((id) => {
              const route = state.routes.get(id);
              return (
                <div className="route-item" key={id}>
                  <div className="route-ref">{routeLabel(route)}</div>
                  <div className="route-name">
                    {route.tags.from}
                    {route.tags.to ? " → " + route.tags.to : ""}
                    {route.tags.operator ? " · " + route.tags.operator : ""}
                  </div>
                </div>
              );
            })}
            {!state.compatibleRouteIds.size && (
              <p>Nenhuma linha mapeada atende aos pontos nesta ordem.</p>
            )}
          </div>
        </section>
      )}
      <div className="search-controls">
        <form
          className="floating-search"
          onSubmit={(e) => {
            e.preventDefault();
            if (address.trim()) load();
          }}
        >
          <input
            type="search"
            required
            maxLength={300}
            value={address}
            onChange={(e) => setAddress(e.target.value)}
            placeholder="Informe um endereço em Mauá"
            aria-label="Endereço"
            autoComplete="street-address"
          />
          <button type="submit" disabled={busy} aria-label="Buscar endereço">
            ⌕
          </button>
        </form>
        <label className="state-select-wrap">
          <span className="sr-only">Estado</span>
          <select
            aria-label="Estado do endereço"
            value={uf}
            onChange={(e) => setUf(e.target.value)}
          >
            {states.map((value) => (
              <option key={value}>{value}</option>
            ))}
          </select>
        </label>
      </div>
      <button
        className="location-button"
        disabled={busy}
        onClick={() => load(true)}
      >
        <span className="location-icon" aria-hidden="true">
          ⌖
        </span>
        Minha localização
      </button>
    </div>
  );
}
