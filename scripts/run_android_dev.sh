#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
MOBILE_DIR="$ROOT_DIR/mobile"
BACKEND_HOST="0.0.0.0"
BACKEND_PORT="${BACKEND_PORT:-8000}"
MODE="${1:-device}"
DEVICE_ID="${DEVICE_ID:-}"
POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-second-brain-postgres-dev}"

usage() {
  cat <<'EOF'
Usage:
  scripts/run_android_dev.sh [device|emulator]

Environment:
  API_BASE_URL   Override the mobile backend URL.
  BACKEND_PORT   Override Django port. Default: 8000.
  DEVICE_ID      Optional Flutter device id passed to flutter run -d.
  SKIP_DB_START  Set to 1 if PostgreSQL is already running elsewhere.

Examples:
  scripts/run_android_dev.sh device
  scripts/run_android_dev.sh emulator
  API_BASE_URL=http://192.168.1.50:8000 scripts/run_android_dev.sh device
  DEVICE_ID=emulator-5554 scripts/run_android_dev.sh emulator
EOF
}

if [[ "$MODE" == "-h" || "$MODE" == "--help" ]]; then
  usage
  exit 0
fi

if [[ "$MODE" != "device" && "$MODE" != "emulator" ]]; then
  usage
  exit 2
fi

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

detect_lan_ip() {
  local ip
  ip="$(hostname -I 2>/dev/null | awk '{print $1}')"
  if [[ -n "$ip" ]]; then
    echo "$ip"
    return
  fi

  ip="$(ip route get 8.8.8.8 2>/dev/null | awk '/src/ {for (i=1; i<=NF; i++) if ($i == "src") print $(i+1)}' | head -n1)"
  if [[ -n "$ip" ]]; then
    echo "$ip"
    return
  fi

  echo "Could not detect LAN IP. Set API_BASE_URL manually." >&2
  exit 1
}

api_host() {
  local without_scheme="${API_BASE_URL#*://}"
  local host_port="${without_scheme%%/*}"
  echo "${host_port%%:*}"
}

append_allowed_host() {
  local host="$1"
  local current="${DJANGO_ALLOWED_HOSTS:-localhost,127.0.0.1}"

  if [[ ",$current," != *",$host,"* ]]; then
    current="$current,$host"
  fi

  export DJANGO_ALLOWED_HOSTS="$current"
}

require_command flutter
require_command "$BACKEND_DIR/.venv/bin/python"

load_backend_env() {
  if [[ -f "$BACKEND_DIR/.env" ]]; then
    set -a
    # shellcheck source=/dev/null
    source "$BACKEND_DIR/.env"
    set +a
  fi
}

compose_cmd() {
  if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    echo "docker compose"
    return
  fi

  if command -v docker-compose >/dev/null 2>&1; then
    echo "docker-compose"
    return
  fi

  echo ""
}

wait_for_database() {
  local attempts=30
  local delay=1

  for ((i = 1; i <= attempts; i++)); do
    if "$BACKEND_DIR/.venv/bin/python" manage.py shell -c "from django.db import connection; connection.ensure_connection()" >/dev/null 2>&1; then
      return 0
    fi

    echo "Waiting for PostgreSQL ($i/$attempts)..."
    sleep "$delay"
  done

  echo "PostgreSQL did not become available. Check backend/.env POSTGRES_* values." >&2
  return 1
}

start_database() {
  if [[ "${SKIP_DB_START:-0}" == "1" ]]; then
    return
  fi

  local compose
  compose="$(compose_cmd)"
  if [[ -n "$compose" ]]; then
    cd "$ROOT_DIR"
    echo "Starting PostgreSQL with: $compose up -d postgres"
    if $compose up -d postgres; then
      return
    fi
    echo "Docker Compose failed; falling back to plain docker."
  fi

  require_command docker

  if docker container inspect "$POSTGRES_CONTAINER" >/dev/null 2>&1; then
    echo "Starting existing PostgreSQL container: $POSTGRES_CONTAINER"
    docker start "$POSTGRES_CONTAINER" >/dev/null
    return
  fi

  echo "Creating PostgreSQL container: $POSTGRES_CONTAINER"
  docker run \
    --name "$POSTGRES_CONTAINER" \
    -e "POSTGRES_DB=${POSTGRES_DB:-second_brain}" \
    -e "POSTGRES_USER=${POSTGRES_USER:-second_brain}" \
    -e "POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-second_brain}" \
    -p "${POSTGRES_PORT:-55432}:5432" \
    -d pgvector/pgvector:pg16 >/dev/null
}

load_backend_env

if [[ "$MODE" == "emulator" ]]; then
  API_BASE_URL="${API_BASE_URL:-http://10.0.2.2:$BACKEND_PORT}"
else
  API_BASE_URL="${API_BASE_URL:-http://$(detect_lan_ip):$BACKEND_PORT}"
fi
append_allowed_host "$(api_host)"

echo "Backend: http://$BACKEND_HOST:$BACKEND_PORT"
echo "Mobile API_BASE_URL: $API_BASE_URL"
echo "Django ALLOWED_HOSTS: $DJANGO_ALLOWED_HOSTS"

start_database

cd "$BACKEND_DIR"
"$BACKEND_DIR/.venv/bin/python" manage.py check
wait_for_database
"$BACKEND_DIR/.venv/bin/python" manage.py migrate
"$BACKEND_DIR/.venv/bin/python" manage.py runserver "$BACKEND_HOST:$BACKEND_PORT" &
BACKEND_PID="$!"

cleanup() {
  if kill -0 "$BACKEND_PID" >/dev/null 2>&1; then
    kill "$BACKEND_PID" >/dev/null 2>&1 || true
    wait "$BACKEND_PID" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT INT TERM

sleep 2

cd "$MOBILE_DIR"
flutter pub get

FLUTTER_ARGS=(run --dart-define "API_BASE_URL=$API_BASE_URL")
if [[ -n "$DEVICE_ID" ]]; then
  FLUTTER_ARGS+=(-d "$DEVICE_ID")
fi

flutter "${FLUTTER_ARGS[@]}"
