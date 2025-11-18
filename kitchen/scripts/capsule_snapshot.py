"""Kitchen-native helpers for capsule state snapshots and health checks."""
# @tag: kitchen,scripts,capsule

import json
import subprocess
from datetime import datetime
from pathlib import Path

# Unified snapshot logic

def save_capsule(manifest_path, snapshot_path):
    manifest = json.loads(Path(manifest_path).read_text(encoding='utf-8'))
    state = {
        "capsule": manifest["capsule_name"],
        "version": manifest["version"],
        "created": datetime.utcnow().isoformat() + "Z",
        "environment": manifest["environment"],
        "notebooks": manifest["notebooks"],
        "user": manifest["state"].get("user"),
        "last_run": manifest["state"].get("last_run"),
        "snapshot": manifest["state"].get("snapshot"),
    }
    Path(snapshot_path).write_text(json.dumps(state, indent=2), encoding='utf-8')
    return snapshot_path

def load_capsule(snapshot_path, manifest_path):
    state = json.loads(Path(snapshot_path).read_text(encoding='utf-8'))
    manifest = json.loads(Path(manifest_path).read_text(encoding='utf-8'))
    manifest["state"]["user"] = state.get("user")
    manifest["state"]["last_run"] = state.get("last_run")
    manifest["state"]["snapshot"] = state.get("snapshot")
    Path(manifest_path).write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    return manifest_path

def auto_snapshot(manifest_path="configs/capsules/onboarding.json", snapshot_path="data/capsule-onboarding-snapshot.json"):
    try:
        save_capsule(manifest_path, snapshot_path)
        print("[AutoSnapshot] Capsule state updated.")
    except (OSError, IOError, ValueError) as e:
        print(f"[AutoSnapshot] Capsule snapshot failed: {e}")

# Health checks

def check_dependencies(deps):
    missing = []
    for dep in deps:
        try:
            subprocess.run(["python", "-c", f"import {dep}"], check=True, capture_output=True)
        except subprocess.CalledProcessError:
            missing.append(dep)
    return missing

def check_notebook(notebook_path):
    try:
        import nbformat
        with Path(notebook_path).open(encoding='utf-8') as f:
            nbformat.read(f, as_version=4)
        return True
    except (OSError, IOError, ImportError, nbformat.reader.NotJSONError):
        return False

def check_api(url):
    try:
        import requests
        resp = requests.get(url, timeout=3)
        return resp.status_code == 200
    except (requests.RequestException, ImportError):
        return False

# Multi-capsule/user support

def list_manifests(config_dir="configs/capsules"):
    return [str(p) for p in Path(config_dir).glob("*.json")]

def list_users(manifest_path):
    manifest = json.loads(Path(manifest_path).read_text(encoding='utf-8'))
    users = manifest.get("users", [])
    return users
