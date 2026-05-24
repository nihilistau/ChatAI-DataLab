#!/usr/bin/env bash
set -euo pipefail

if [[ "${SKIP_PREPUSH_CHECKS:-0}" == "1" ]]; then
  echo "[pre-push] Skipping checks because SKIP_PREPUSH_CHECKS=1"
  exit 0
fi

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

pretty() {
  printf '\n[pre-push] %s\n' "$1"
}

pretty "Verifying integrity manifest"
python scripts/project_integrity.py status

pretty "Running backend + notebook tests"
python -m pytest relay/backend/tests -q
python -m pytest tests/test_notebooks.py -q

if [[ -d "relay/frontend/node_modules" ]]; then
  pretty "Running frontend checks"
  (cd relay/frontend && npm run lint -- --max-warnings=0)
  (cd relay/frontend && npm run test -- --runInBand)
  (cd relay/frontend && npm run test:relay -- --runInBand)
else
  pretty "Skipping frontend checks (install dependencies first)"
fi

pretty "Pre-push checks completed"
