"""Process supervisor bridging PowerShell jobs and labctl.sh commands."""

# @tag: controlplane,orchestration

from __future__ import annotations

import json
import os
import platform
import shlex
import shutil
import socket
import subprocess
import time
from pathlib import Path
from typing import Any, Literal

import psutil

Runtime = Literal["auto", "windows", "linux"]
ServiceAction = Literal["start", "stop", "restart", "status", "logs", "kill", "kill-all"]

_SERVICES = ("backend", "frontend", "kitchen")
_DEFAULT_LOG_LINES = 60


class LabOrchestrator:
    """Cross-platform orchestration helper that bridges PowerShell jobs and labctl.sh."""

    def __init__(self, root: Path | None = None):
        self.root = Path(root or Path(__file__).resolve().parents[1]).resolve()
        self.scripts_dir = self.root / "scripts"
        self.labctl = self.scripts_dir / "labctl.sh"
        self.ps_module = self.scripts_dir / "powershell" / "LabControl.psm1"
        self.log_dir = self.root / ".labctl" / "logs"
        self.state_dir = self.root / ".labctl" / "state"
        self._pwsh = shutil.which("pwsh") or shutil.which("powershell")
        self._bash = shutil.which("bash")
        self._wsl = shutil.which("wsl")
        self._system = platform.system().lower()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def snapshot(self, include_logs: bool = True) -> dict[str, Any]:
        services: list[dict[str, Any]] = []
        services.extend(self._windows_job_snapshot())
        services.extend(self._labctl_snapshot())
        processes = self._process_snapshot()
        network = self._network_snapshot()
        logs = self._log_tail_map(_DEFAULT_LOG_LINES) if include_logs else {}
        return {
            "services": services,
            "processes": processes,
            "network": network,
            "logs": logs,
            "timestamp": time.time(),
        }

    def dispatch(
        self,
        action: ServiceAction,
        target: str | None = None,
        *,
        runtime: Runtime = "auto",
        log_lines: int = _DEFAULT_LOG_LINES,
    ) -> dict[str, Any]:
        runtime = self._resolve_runtime(runtime)
        target = target or "all"
        output = ""
        if action == "start":
            output = self._start_service(target, runtime)
        elif action == "stop":
            output = self._stop_service(target, runtime, force=False)
        elif action == "kill":
            output = self._stop_service(target, runtime, force=True)
        elif action == "restart":
            self._stop_service(target, runtime, force=True)
            output = self._start_service(target, runtime)
        elif action == "status":
            output = json.dumps(self.snapshot(include_logs=False), indent=2)
        elif action == "logs":
            output = "\n".join(self._log_tail(target, log_lines))
        elif action == "kill-all":
            self._stop_service("all", runtime, force=True)
            output = "force-stopped all registered services"
        else:
            raise ValueError(f"Unsupported action: {action}")

        return {
            "action": action,
            "target": target,
            "runtime": runtime,
            "output": output.strip(),
            "timestamp": time.time(),
        }

    # ------------------------------------------------------------------
    # Service lifecycle helpers
    # ------------------------------------------------------------------
    def _start_service(self, target: str, runtime: Runtime) -> str:
        if runtime == "windows":
            return self._invoke_pwsh(self._build_ps_start(target))
        return self._run_labctl(self._build_labctl_args("start", target))

    def _stop_service(self, target: str, runtime: Runtime, *, force: bool) -> str:
        if runtime == "windows":
            cmd = self._build_ps_stop(target, force=force)
            return self._invoke_pwsh(cmd)
        verb = "stop-all" if target == "all" else "stop"
        args = [verb]
        if target != "all":
            args.append(target)
        if force and verb == "stop":
            args.append("--force")
        if force and verb == "stop-all":
            verb = "kill-all"
            args = [verb]
        return self._run_labctl(args)

    # ------------------------------------------------------------------
    # Snapshot helpers
    # ------------------------------------------------------------------
    def _windows_job_snapshot(self) -> list[dict[str, Any]]:
        if self._system != "windows" or not self._pwsh:
            return []
        script = (
            "Import-Module '{module}' -Force; "
            "$jobs = Get-LabJobSnapshot; $jobs | ConvertTo-Json -Compress"
        ).format(module=self.ps_module.as_posix())
        try:
            output = self._run_shell([self._pwsh, "-NoLogo", "-NoProfile", "-Command", script])
        except RuntimeError:
            return []
        try:
            data = json.loads(output) if output else []
        except json.JSONDecodeError:
            return []
        if isinstance(data, dict):
            data = [data]
        for item in data:
            item["runtime"] = "windows"
        return data

    def _labctl_snapshot(self) -> list[dict[str, Any]]:
        if not self.labctl.exists():
            return []
        try:
            raw = self._run_labctl(["status", "--json"])
            data = json.loads(raw)
        except (RuntimeError, json.JSONDecodeError):
            return []
        for item in data:
            item.setdefault("runtime", "linux")
        return data

    def _process_snapshot(self, limit: int = 12) -> list[dict[str, Any]]:
        entries: list[dict[str, Any]] = []
        now = time.time()
        for proc in psutil.process_iter(attrs=["pid", "name", "username", "create_time", "cpu_percent", "memory_percent", "cmdline"]):
            try:
                info = proc.info
                uptime = max(0.0, now - (info.get("create_time") or now))
                entries.append(
                    {
                        "pid": info.get("pid"),
                        "name": info.get("name"),
                        "username": info.get("username"),
                        "cpu": round(info.get("cpu_percent") or 0.0, 2),
                        "memory": round(info.get("memory_percent") or 0.0, 2),
                        "uptime": int(uptime),
                        "cmdline": info.get("cmdline") or [],
                    }
                )
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        entries.sort(key=lambda item: item["cpu"], reverse=True)
        return entries[:limit]

    def _network_snapshot(self) -> dict[str, Any]:
        boot_time = psutil.boot_time()
        net_counters = psutil.net_io_counters()
        iface_stats = psutil.net_if_stats()
        return {
            "hostname": socket.gethostname(),
            "platform": platform.platform(),
            "uptime": int(time.time() - boot_time),
            "bytes_sent": net_counters.bytes_sent if net_counters else 0,
            "bytes_recv": net_counters.bytes_recv if net_counters else 0,
            "interfaces": {name: {"isup": stats.isup, "speed": stats.speed} for name, stats in iface_stats.items()},
        }

    # ------------------------------------------------------------------
    # Logging helpers
    # ------------------------------------------------------------------
    def _log_tail_map(self, lines: int) -> dict[str, list[str]]:
        log_map: dict[str, list[str]] = {}
        for service in _SERVICES:
            log_map[service] = self._log_tail(service, lines)
        return log_map

    def _log_tail(self, service: str, lines: int) -> list[str]:
        log_path = self.log_dir / f"{service}.log"
        if not log_path.exists():
            return []
        with log_path.open("r", encoding="utf-8", errors="ignore") as handle:
            content = handle.readlines()
        return [line.rstrip("\n") for line in content[-lines:]]

    # ------------------------------------------------------------------
    # Shell helpers
    # ------------------------------------------------------------------
    def _run_labctl(self, args: list[str]) -> str:
        if self._system == "windows" and self._pwsh:
            quoted = ", ".join(shlex.quote(arg) for arg in args)
            script = (
                f"Import-Module '{self.ps_module.as_posix()}' -Force; "
                f"$arguments = @({quoted}); "
                "Invoke-LabUnixControl @arguments -PassThru"
            )
            return self._run_shell([self._pwsh, "-NoLogo", "-NoProfile", "-Command", script])

        if self._system == "windows" and self._bash:
            cmd = [self._bash, "-lc", f"cd '{self.root.as_posix()}' && ./scripts/labctl.sh {' '.join(shlex.quote(arg) for arg in args)}"]
            return self._run_shell(cmd)

        cmd = [str(self.labctl), *args]
        return self._run_shell(cmd)

    def _invoke_pwsh(self, payload: str) -> str:
        if not self._pwsh:
            raise RuntimeError("PowerShell is not available on this host.")
        script = f"Import-Module '{self.ps_module.as_posix()}' -Force; {payload}"
        return self._run_shell([self._pwsh, "-NoLogo", "-NoProfile", "-Command", script])

    def _run_shell(self, cmd: list[str]) -> str:
        completed = subprocess.run(cmd, capture_output=True, text=True, cwd=self.root)
        if completed.returncode != 0:
            stderr = completed.stderr.strip()
            stdout = completed.stdout.strip()
            message = stderr or stdout or "Command failed"
            raise RuntimeError(message)
        return completed.stdout.strip()

    def _build_ps_start(self, target: str) -> str:
        if target == "all":
            return "Start-AllLabJobs"
        return f"Start-LabJob -Name {target} -Force"

    def _build_ps_stop(self, target: str, *, force: bool) -> str:
        if target == "all":
            return "Stop-AllLabJobs -Force"
        flag = " -Force" if force else ""
        return f"Stop-LabJob -Name {target}{flag}"

    def _build_labctl_args(self, command: str, target: str) -> list[str]:
        if target == "all":
            return [f"{command}-all"] if command in {"start", "stop"} else [command]
        return [command, target]

    def _resolve_runtime(self, runtime: Runtime) -> Runtime:
        if runtime != "auto":
            return runtime
        return "windows" if self._system == "windows" else "linux"


def get_default_orchestrator() -> LabOrchestrator:
    global _ORCHESTRATOR_INSTANCE
    try:
        return _ORCHESTRATOR_INSTANCE  # type: ignore[name-defined]
    except NameError:
        _ORCHESTRATOR_INSTANCE = LabOrchestrator()
        return _ORCHESTRATOR_INSTANCE
