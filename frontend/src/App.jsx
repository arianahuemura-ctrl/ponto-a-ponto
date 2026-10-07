import { lazy, Suspense } from "react";
import Passenger from "./Passenger.jsx";
import "./passenger.css";
import "./passenger-responsive.css";
const SaoPaulo = lazy(() => import("./SaoPaulo.jsx"));
const Explorer = lazy(() => import("./ExplorerEntry.jsx"));
export default function App() {
  if (location.pathname === "/explorar/")
    return (
      <Suspense fallback={<p>Carregando mapa…</p>}>
        <Explorer />
      </Suspense>
    );
  const params = new URLSearchParams(location.search);
  const legacyStop = /^(way|node|relation):/.test(params.get("stop") || "");
  if (params.get("city") === "maua" || legacyStop) return <Passenger />;
  return <Suspense fallback={<p>Carregando São Paulo…</p>}><SaoPaulo /></Suspense>;
}
