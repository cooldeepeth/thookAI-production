// TODO: Add Sentry error tracking
// npm install @sentry/react
// Then initialize with REACT_APP_SENTRY_DSN env var

import React from "react";
import ReactDOM from "react-dom/client";
import "@/index.css";
import App from "@/App";

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
