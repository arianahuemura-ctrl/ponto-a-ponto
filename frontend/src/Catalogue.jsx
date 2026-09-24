import { useEffect, useState } from "react";
import { api } from "./api.js";

export default function Catalogue() {
  const [data, setData] = useState(null);
  const [query, setQuery] = useState("");
  const [detail, setDetail] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    api("catalogue", {}, controller.signal).then(setData).catch((e) => {
      if (!controller.signal.aborted) setError(e.message);
    });
    return () => controller.abort();
  }, []);
  const show = async (id) => {
    setError("");
    setDetail(null);
    try { setDetail(await api("catalogue/routes/" + encodeURIComponent(id))); }
    catch (e) { setError(e.message); }
  };
  return <section className="screen-content">
    <h2>Linhas e pontos cadastrados</h2>
    <p>Fontes públicas consultadas. Sentidos e variantes são apresentados separadamente; a cobertura ainda é parcial.</p>
    {error && <p role="alert">{error}</p>}
    {!data && !error && <p>Carregando cadastro…</p>}
    {data && <>
      <p>{data.counts.stops} registros de paradas, {data.counts.located_stops} com coordenadas. Os registros de fontes diferentes ainda precisam de conciliação.</p>
      <label>Buscar linha<input value={query} onChange={e => setQuery(e.target.value)} placeholder="Número ou destino" /></label>
      {detail && <article aria-live="polite">
        <h3>{detail.code} — {detail.name}</h3>
        <p>{detail.source} · {detail.routable ? "Disponível para planejamento" : "Sem dados suficientes para planejamento e acompanhamento no mapa"}</p>
        {detail.source_url && <a href={detail.source_url} target="_blank" rel="noreferrer">Consultar itinerário e horários na fonte</a>}
        <p>{detail.street_itinerary}</p>
        <ol>{detail.stops.map((s,i) => <li key={i}>{s.name}{s.lat == null ? " · localização pendente" : s.geolocation?.status === "estimated" ? " · posição aproximada" : ""}{s.route_estimate && <small> · Sentido {s.route_estimate.status === "estimated" ? "estimado pelo itinerário" : "pendente de revisão"}</small>}</li>)}</ol>
        {!detail.stops.length && <p>A fonte foi registrada, mas não forneceu uma sequência de paradas importável.</p>}
      </article>}
      <div className="line-list">{data.routes.filter(r => `${r.code} ${r.name} ${r.source}`.toLowerCase().includes(query.toLowerCase())).map(r => <button className="secondary full" key={r.id} onClick={() => show(r.id)}>{r.code} — {r.name} · {r.source} · {r.stop_count} paradas</button>)}</div>
      <details><summary>Fontes e situação da coleta</summary>{data.sources.map((s,i) => <p key={i}><a href={s.url} target="_blank" rel="noreferrer">{s.provider}</a> — {s.status === "ok" ? "Documento disponível" : "Coleta indisponível"}{s.retrieved_at ? ` · ${new Date(s.retrieved_at).toLocaleDateString("pt-BR")}` : ""}</p>)}</details>
    </>}
  </section>;
}
