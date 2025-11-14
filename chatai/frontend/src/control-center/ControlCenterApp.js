import { jsx as _jsx } from "react/jsx-runtime";
import { ControlCenterProvider } from "./context";
import { ControlCenterShell } from "./ControlCenterShell";
export default function ControlCenterApp() {
    return (_jsx(ControlCenterProvider, { children: _jsx(ControlCenterShell, {}) }));
}
