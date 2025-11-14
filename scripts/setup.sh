#!/usr/bin/env bash
# @tag: scripts,shell,setup
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_NAME=".venv"

log() {
	printf "[%s] %s\n" "$(date '+%H:%M:%S')" "$*"
}

detect_pkg_manager() {
	if command -v apt-get >/dev/null 2>&1; then
		echo "apt"
	elif command -v pacman >/dev/null 2>&1; then
		echo "pacman"
	else
		echo "manual"
	fi
}

install_system_packages() {
	local pkg_mgr="$1"
	local debian_packages=(python3 python3-venv python3-pip nodejs npm git)
	local arch_packages=(python python-virtualenv python-pip nodejs npm git)
	case "$pkg_mgr" in
		apt)
			log "🚀 Updating apt repositories"
			sudo apt-get update -y
			log "📦 Installing base packages via apt"
			sudo apt-get install -y "${debian_packages[@]}"
			;;
		pacman)
			log "🚀 Refreshing pacman databases"
			sudo pacman -Sy --noconfirm
			log "📦 Installing base packages via pacman"
			sudo pacman -S --needed --noconfirm "${arch_packages[@]}"
			;;
		manual)
			log "⚠️  Unable to detect apt or pacman. Please install python3, python3-venv, pip, nodejs, npm, and git manually."
			;;
	esac
}

python_bin() {
	if command -v python3 >/dev/null 2>&1; then
		echo "python3"
	elif command -v python >/dev/null 2>&1; then
		echo "python"
	else
		log "❌ Python 3 runtime not found. Please install python3 or ensure it is on PATH."
		exit 1
	fi
}

create_python_env() {
	local dir="$1"
	local py
	py="$(python_bin)"
	"$py" -m venv "$dir/$VENV_NAME"
	# shellcheck disable=SC1090
	source "$dir/$VENV_NAME/bin/activate"
	pip install --upgrade pip
	pip install -r "$dir/requirements.txt"
	deactivate
}

setup_backend() {
	local path="$ROOT_DIR/chatai/backend"
	log "⚙️  Setting up backend in $path"
	create_python_env "$path"
}

setup_frontend() {
	local path="$ROOT_DIR/chatai/frontend"
	log "🧱 Installing frontend dependencies"
	(cd "$path" && npm install && npm run build)
}

setup_datalab() {
	local path="$ROOT_DIR/datalab"
	log "🧪 Setting up DataLab"
	create_python_env "$path"
}

fetch_assets() {
	local script_path="$ROOT_DIR/scripts/fetch_assets.sh"
	if [[ -x "$script_path" ]]; then
		log "📂 Fetching external assets"
		(cd "$ROOT_DIR" && "$script_path")
	else
		log "ℹ️  Skipping asset download (scripts/fetch_assets.sh not found or not executable)"
	fi
}

main() {
	log "🚀 Starting ChatAI · DataLab setup"
	local pkg_mgr
	pkg_mgr="$(detect_pkg_manager)"
	install_system_packages "$pkg_mgr"
	setup_backend
	setup_frontend
	setup_datalab
	fetch_assets
	log "✅ Setup complete"
	cat <<'EOT'
Next steps:
  • Backend:   cd chatai/backend && source .venv/bin/activate && uvicorn main:app --host 0.0.0.0 --port 8000
  • Frontend:  cd chatai/frontend && npm run dev -- --host
  • DataLab:   cd datalab && source .venv/bin/activate && jupyter lab --ip 0.0.0.0 --no-browser
EOT
}

main "$@"