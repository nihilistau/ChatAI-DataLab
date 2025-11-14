import { jsx as _jsx } from "react/jsx-runtime";
/** Entry point for the Control Center Playground UI. */
// @tag: frontend,entrypoint,control
import React from "react";
import ReactDOM from "react-dom/client";
import ControlCenterApp from "./control-center/ControlCenterApp";
import "./styles.css";
import "./control-center/styles.css";
document.body.classList.add("control-center-body");
ReactDOM.createRoot(document.getElementById("root")).render(_jsx(React.StrictMode, { children: _jsx(ControlCenterApp, {}) }));
