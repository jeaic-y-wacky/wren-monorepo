#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
SRC_DIR="${WREN_E2E_SRC_DIR:-${BACKEND_DIR}/../wren_src}"
PORT="${WREN_E2E_PORT:-8000}"
BASE_URL="http://127.0.0.1:${PORT}"
API_KEY="${WREN_E2E_API_KEY:-test_user_12345678}"

if ! command -v uv >/dev/null 2>&1; then
  echo "Missing required command: uv" >&2
  exit 1
fi

if ! command -v curl >/dev/null 2>&1; then
  echo "Missing required command: curl" >&2
  exit 1
fi

if [[ ! -d "$SRC_DIR" ]]; then
  echo "wren_src not found at $SRC_DIR" >&2
  exit 1
fi

TMP_DIR="$(mktemp -d)"
SCRIPT_PATH="${TMP_DIR}/sample_script.py"
LOG_PATH="${TMP_DIR}/backend.log"
SERVER_PID=""

cleanup() {
  if [[ -n "${SERVER_PID}" ]]; then
    kill "${SERVER_PID}" >/dev/null 2>&1 || true
    wait "${SERVER_PID}" >/dev/null 2>&1 || true
  fi
  rm -rf "${TMP_DIR}"
}
trap cleanup EXIT

cat > "${SCRIPT_PATH}" <<'PY'
import wren

@wren.on_schedule("0 9 * * *")
def daily_report():
    return "ok"
PY

uv run --project "${BACKEND_DIR}" uvicorn wren_backend.main:app \
  --host 127.0.0.1 \
  --port "${PORT}" \
  >"${LOG_PATH}" 2>&1 &
SERVER_PID=$!

ready=0
for _ in {1..40}; do
  if curl -fsS "${BASE_URL}/health" >/dev/null 2>&1; then
    ready=1
    break
  fi
  if ! kill -0 "${SERVER_PID}" >/dev/null 2>&1; then
    echo "Backend process exited early. Log output:" >&2
    sed -n '1,200p' "${LOG_PATH}" >&2
    exit 1
  fi
  sleep 0.25
done

if [[ "${ready}" -ne 1 ]]; then
  echo "Backend did not become ready." >&2
  sed -n '1,200p' "${LOG_PATH}" >&2
  exit 1
fi

WREN_PLATFORM_URL="${BASE_URL}" WREN_PLATFORM_API_KEY="${API_KEY}" \
  uv run --project "${SRC_DIR}" wren test "${SCRIPT_PATH}"

WREN_PLATFORM_URL="${BASE_URL}" WREN_PLATFORM_API_KEY="${API_KEY}" \
  uv run --project "${SRC_DIR}" wren validate "${SCRIPT_PATH}"

DEPLOY_JSON="$(
  WREN_PLATFORM_URL="${BASE_URL}" WREN_PLATFORM_API_KEY="${API_KEY}" \
  uv run --project "${SRC_DIR}" wren deploy "${SCRIPT_PATH}" --json
)"

DEPLOYMENT_ID="$(
  printf '%s' "${DEPLOY_JSON}" | uv run --project "${BACKEND_DIR}" python - <<'PY'
import json
import sys

data = json.load(sys.stdin)
if not data.get("valid"):
    raise SystemExit(f"Deployment failed: {data.get('error')}")
deployment_id = data.get("deployment_id")
if not deployment_id:
    raise SystemExit("Missing deployment_id in response")
print(deployment_id)
PY
)"

curl -fsS -H "X-API-Key: ${API_KEY}" \
  "${BASE_URL}/v1/deployments/${DEPLOYMENT_ID}" >/dev/null

echo "E2E OK: deployment ${DEPLOYMENT_ID}"
