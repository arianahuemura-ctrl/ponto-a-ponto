import { lazy, Suspense } from "react";
import Passenger from "./Passenger.jsx";
import "./passenger.css";
const Explorer = lazy(() => import("./ExplorerEntry.jsx"));
export default function App() {
  if (location.pathname === "/explorar/")
    return (
      <Suspense fallback={<p>Carregando mapa…</p>}>
        <Explorer />
      </Suspense>
    );
  return <Passenger />;
}
