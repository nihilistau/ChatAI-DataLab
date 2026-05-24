import React from "react";
import { ControlCenterProvider } from "./context";
import { ControlCenterShell } from "./ControlCenterShell";

export default function ControlCenterApp() {
  return (
    <ControlCenterProvider>
      <ControlCenterShell />
    </ControlCenterProvider>
  );
}
