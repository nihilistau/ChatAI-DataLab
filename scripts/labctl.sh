#!/usr/bin/env bash
# @tag: scripts,shell,lab-control
# ChatAI · Kitchen Linux control utility
# Usage: scripts/labctl.sh <command> [args]
# Environment:
#   LAB_REMOTE_PATH - default remote project path for the `remote` subcommand (defaults to ~/ChatAI-DataLab)
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="$ROOT_DIR/.labctl/state"
LOG_DIR="$ROOT_DIR/.labctl/logs"
DEFAULT_REMOTE_PATH="${LAB_REMOTE_PATH:-~/ChatAI-DataLab}"

mkdir -p "$STATE_DIR" "$LOG_DIR"

declare -A JOB_CMD JOB_CWD JOB_ENV

ensure_job() {
    local name="$1"
    if [[ -z "${JOB_CMD[$name]:-}" ]]; then
        echo "Unknown job: $name"
        exit 1
    fi
}

register_job() {
    local name="$1"
    local cwd="$2"
    local cmd="$3"
    local env="$4"
    JOB_CMD["$name"]="$cmd"
    JOB_CWD["$name"]="$cwd"
    JOB_ENV["$name"]="$env"
}

register_job "backend" "$ROOT_DIR/playground/backend" "uvicorn main:app --host 0.0.0.0 --port 8000" "PYTHONPATH=$ROOT_DIR/playground/backend"
register_job "frontend" "$ROOT_DIR/playground/frontend" "npm run dev -- --host" ""
register_job "kitchen" "$ROOT_DIR/kitchen" "jupyter lab --ip=0.0.0.0 --no-browser" ""

list_jobs() {
    printf "%s\n" "${!JOB_CMD[@]}" | sort
}

pid_file() { echo "$STATE_DIR/$1.pid"; }
log_file() { echo "$LOG_DIR/$1.log"; }

is_running() {
    local name="$1"; local file
    file="$(pid_file "$name")"
    if [[ -f "$file" ]]; then
        local pid
        pid="$(<"$file")"
        if kill -0 "$pid" >/dev/null 2>&1; then
            return 0
        fi
    fi
    return 1
}

export_env_for_job() {
    local name="$1"; local env_string="${JOB_ENV[$name]:-}"
    if [[ -z "$env_string" ]]; then
        return
    fi
    IFS=';' read -ra pairs <<<"$env_string"
    for pair in "${pairs[@]}"; do
        if [[ -n "$pair" ]]; then
            export "$pair"
        fi
    done
}

start_job() {
    local name="$1"
    ensure_job "$name"
    if is_running "$name"; then
        echo "[$name] already running"
        return
    fi
    local logfile
    logfile="$(log_file "$name")"
    touch "$logfile"
    printf '\n[%s] starting %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$name" >>"$logfile"
    (
        cd "${JOB_CWD[$name]}"
        export_env_for_job "$name"
        nohup bash -c "${JOB_CMD[$name]}" >>"$logfile" 2>&1 &
        echo $! >"$(pid_file "$name")"
    )
    echo "[$name] started (PID $(<"$(pid_file "$name")"))"
}

stop_job() {
    local name="$1"
    ensure_job "$name"
    if ! is_running "$name"; then
        echo "[$name] not running"
        rm -f "$(pid_file "$name")"
        return
    fi
    local pid
    pid="$(<"$(pid_file "$name")")"
    kill "$pid" >/dev/null 2>&1 || true
    timeout=10
    while kill -0 "$pid" >/dev/null 2>&1 && (( timeout > 0 )); do
        sleep 1
        ((timeout--))
    done
    if kill -0 "$pid" >/dev/null 2>&1; then
        kill -9 "$pid" >/dev/null 2>&1 || true
    fi
    rm -f "$(pid_file "$name")"
    echo "[$name] stopped"
}

status_job() {
    local name="$1"
    ensure_job "$name"
    if is_running "$name"; then
        local pid
        pid="$(<"$(pid_file "$name")")"
        echo "$name: running (PID $pid)"
    else
        echo "$name: stopped"
    fi
}

status_all_json() {
    local first=1
    printf '['
    for job in $(list_jobs); do
        local pid=""
        local uptime=0
        local state="stopped"
        if is_running "$job"; then
            pid="$(<"$(pid_file "$job")")"
            state="running"
            if command -v ps >/dev/null 2>&1; then
                uptime="$(ps -p "$pid" -o etimes= 2>/dev/null | tr -d ' ')"
                [[ -z "$uptime" ]] && uptime=0
            fi
        fi
        if [[ $first -eq 0 ]]; then
            printf ','
        fi
        printf '\n  {"name":"%s","state":"%s","pid":"%s","uptime":%s,"logPath":"%s"}' \
            "$job" "$state" "$pid" "$uptime" "$(log_file "$job")"
        first=0
    done
    printf '\n]'
}

logs_job() {
    local name="$1"
    ensure_job "$name"
    local logfile
    logfile="$(log_file "$name")"
    touch "$logfile"
    tail -f "$logfile"
}

start_all() { for job in $(list_jobs); do start_job "$job"; done; }
stop_all() { for job in $(list_jobs); do stop_job "$job"; done; }
kill_all() { for job in $(list_jobs); do stop_job "$job"; done; rm -f "$STATE_DIR"/*.pid 2>/dev/null || true; }
status_all() { for job in $(list_jobs); do status_job "$job"; done; }

backup_workspace() {
    local dest="$1"
    local default_name="workspace-$(date '+%Y%m%d-%H%M%S').tar.gz"
    [[ -n "$dest" ]] || dest="$ROOT_DIR/backups/$default_name"
    mkdir -p "$(dirname "$dest")"
    tar -czf "$dest" -C "$ROOT_DIR" playground kitchen data scripts
    echo "Backup written to $dest"
}

restore_workspace() {
    local archive="$1"
    [[ -f "$archive" ]] || { echo "Archive not found: $archive"; exit 1; }
    tar -xzf "$archive" -C "$ROOT_DIR"
}

run_install() {
    bash "$ROOT_DIR/scripts/setup.sh"
}

remote_exec() {
    local host="$1"; shift
    local remote_path="$1"; shift
    local remote_cmd
    printf -v remote_cmd '%q ' "$@"
    ssh "$host" "cd '$remote_path' && ./scripts/labctl.sh ${remote_cmd% }"
}

usage() {
    cat <<'HELP'
Usage: scripts/labctl.sh <command> [args]
Commands:
  start <job>        Start a specific job
  stop <job>         Stop a job
  restart <job>      Restart a job
  status [job]       Show status for one or all jobs
    status --json      Machine-readable job snapshot
  logs <job>         Stream logs for a job
  start-all          Start every job
  stop-all           Stop every job
    kill-all           Force stop and clear all PID files
  backup [path]      Create a tar.gz backup (optional destination)
  restore <path>     Restore from a backup archive
  install            Run the Linux installer (scripts/setup.sh)
  remote <host> [path] <subcommand...>
                     Run a subcommand on a remote host over SSH
HELP
}

if [[ $# -lt 1 ]]; then
    usage
    exit 1
fi

case "$1" in
    start) shift; start_job "$1" ;;
    stop) shift; stop_job "$1" ;;
    restart) shift; stop_job "$1"; start_job "$1" ;;
    status)
        shift || true
        if [[ "${1:-}" == "--json" ]]; then
            shift || true
            status_all_json
        elif [[ -n "${1:-}" ]]; then
            status_job "$1"
        else
            status_all
        fi
        ;;
    logs) shift; logs_job "$1" ;;
    start-all) start_all ;;
    stop-all) stop_all ;;
    kill-all) kill_all ;;
    backup)
        shift || true
        backup_workspace "${1:-}"
        ;;
    restore) shift; restore_workspace "$1" ;;
    install) run_install ;;
    remote)
        shift
        [[ $# -ge 2 ]] || { echo "remote requires <host> <subcommand>"; exit 1; }
        local host="$1"; shift
        local maybe_path="$1"
        if [[ "$maybe_path" == /* || "$maybe_path" == ~* ]]; then
            shift
            remote_exec "$host" "$maybe_path" "$@"
        else
            remote_exec "$host" "$DEFAULT_REMOTE_PATH" "$maybe_path" "$@"
        fi
        ;;
    *) usage; exit 1 ;;
 esac
