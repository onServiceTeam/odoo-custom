#!/usr/bin/env bash
# ─── Safe Test Runner ──────────────────────────────────────────────────────────
# Always targets onservice_test_db — NEVER production.
# Usage:  ./scripts/run-tests.sh [module1,module2,...]
# Default: all custom modules
set -euo pipefail

TEST_DB="onservice_test_db"
PROD_DB="onservice_prod_db"
DB_HOST="odoo-db"
DB_PORT="5432"
DB_USER="odoo"
DB_PASS="***REMOVED***"

ALL_MODULES="ons_ops_core,ons_ops_shell,ons_ops_intake,ons_discuss_ui,ons_discuss_threads,ons_discuss_voice,ons_gif_provider,ons_webrtc,discuss_thread_admin"
MODULES="${1:-$ALL_MODULES}"

# Safety: refuse to run against production
if [[ "$MODULES" == *"$PROD_DB"* ]]; then
    echo "ABORT: refusing to run tests against production database." >&2
    exit 1
fi

# Ensure test DB exists — recreate from prod template if missing
if ! sudo docker exec "$DB_HOST" psql -U "$DB_USER" -d postgres -tAc \
    "SELECT 1 FROM pg_database WHERE datname='$TEST_DB'" | grep -q 1; then
    echo "Creating test database '$TEST_DB' from '$PROD_DB'..."
    sudo docker exec "$DB_HOST" psql -U "$DB_USER" -d postgres -c \
        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='$PROD_DB' AND pid <> pg_backend_pid();" >/dev/null 2>&1
    sudo docker exec "$DB_HOST" createdb -U "$DB_USER" -T "$PROD_DB" "$TEST_DB"
fi

echo "Running tests on $TEST_DB for modules: $MODULES"
sudo docker exec odoo-web odoo \
    -d "$TEST_DB" \
    --db_host="$DB_HOST" --db_port="$DB_PORT" \
    --db_user="$DB_USER" --db_password="$DB_PASS" \
    --test-enable \
    -u "$MODULES" \
    --stop-after-init --no-http 2>&1 \
    | grep -E "Starting.*test_|failures|FAIL|ERROR.*Test|Modules loaded|tests\.stats"

echo "---"
echo "Test run complete against $TEST_DB (NOT production)."
