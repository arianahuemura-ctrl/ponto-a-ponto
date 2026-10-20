import React from "react";
import { createRoot } from "react-dom/client";
import Feedback from './Feedback.jsx';
import App from "./App.jsx";
import UsabilityConsent from "./UsabilityConsent.jsx";
import "leaflet/dist/leaflet.css";

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <UsabilityConsent><App /><Feedback /></UsabilityConsent>
  </React.StrictMode>,
);
