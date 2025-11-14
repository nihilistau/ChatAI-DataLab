/** Entry for the Vite-powered SPA that mounts the ChatAI DataLab shell. */
// @tag: frontend,entrypoint

import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
