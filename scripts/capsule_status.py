import json
from pathlib import Path
from datetime import datetime
import time
import subprocess
from kitchen.scripts.capsule_snapshot import (
    check_dependencies,
    check_notebook,
    check_api,
)

def get_capsule_status(manifest_path, snapshot_path, log_path=None):
    manifest = json.loads(Path(manifest_path).read_text(encoding='utf-8'))
    snapshot = None
    if Path(snapshot_path).exists():
        snapshot = json.loads(Path(snapshot_path).read_text(encoding='utf-8'))
    # Health checks
    deps = manifest.get("environment", {}).get("dependencies", [])
    missing_deps = check_dependencies(deps) if deps else []
    notebooks = manifest.get("notebooks", [])
    notebook_health = {nb: check_notebook(nb) for nb in notebooks}
    api_url = manifest.get("environment", {}).get("api_url")
    api_health = check_api(api_url) if api_url else None
    # Integrity status
    try:
        integrity = subprocess.run([
            "python", "scripts/project_integrity.py", "status", "--json"
        ], capture_output=True, text=True, check=True)
        integrity_status = json.loads(integrity.stdout)
    except Exception as e:
        integrity_status = {"error": str(e)}

    # SearchToolkit bug-hunt sweep
    try:
        bughunt = subprocess.run([
            "pwsh", "-File", "scripts/powershell/SearchToolkit.psm1", "Search-LabRepo", "-Preset", "bug-hunt", "-Output", "json"
        ], capture_output=True, text=True, check=True)
        bughunt_status = json.loads(bughunt.stdout)
    except Exception as e:
        bughunt_status = {"error": str(e)}

    status = {
        "capsule": manifest["capsule_name"],
        "version": manifest["version"],
        "last_run": manifest["state"].get("last_run"),
        "user": manifest["state"].get("user"),
        "snapshot_exists": Path(snapshot_path).exists(),
        "snapshot_created": snapshot.get("created") if snapshot else None,
        "notebooks": manifest["notebooks"],
        "notebook_health": notebook_health,
        "missing_dependencies": missing_deps,
        "api_health": api_health,
        "artifact_folder": "release_artifacts/",
        "artifact_retained": Path("release_artifacts/").exists(),
        "status_checked": datetime.utcnow().isoformat() + "Z",
        "integrity": integrity_status,
        "bughunt": bughunt_status
    }
    print(json.dumps(status, indent=2))
    if log_path:
        with open(log_path, "a", encoding='utf-8') as f:
            f.write(json.dumps(status) + "\n")

def cleanup_artifacts(artifact_dir="release_artifacts/", retention_days=30):
    now = time.time()
    cutoff = now - retention_days * 86400
    removed_artifacts = []
    if Path(artifact_dir).exists():
        for item in Path(artifact_dir).iterdir():
            if item.is_file() and item.stat().st_mtime < cutoff:
                item.unlink()
                removed_artifacts.append(str(item))
    return removed_artifacts

def periodic_status(manifest_path, snapshot_path, log_path, interval=3600):
    while True:
        get_capsule_status(manifest_path, snapshot_path, log_path)
        cleanup_artifacts()
        time.sleep(interval)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Capsule status reporter")
    parser.add_argument("--manifest", default="configs/capsules/onboarding.json")
    parser.add_argument("--snapshot", default="data/capsule-onboarding-snapshot.json")
    parser.add_argument("--log", default="logs/capsule_status.jsonl")
    parser.add_argument("--periodic", action="store_true", help="Run periodic status checks")
    parser.add_argument("--interval", type=int, default=3600, help="Interval in seconds for periodic checks")
    args = parser.parse_args()
    if args.periodic:
        periodic_status(args.manifest, args.snapshot, args.log, args.interval)
    else:
        get_capsule_status(args.manifest, args.snapshot, args.log)
        removed_files = cleanup_artifacts()
        if removed_files:
            print(f"Removed old artifacts: {removed_files}")
