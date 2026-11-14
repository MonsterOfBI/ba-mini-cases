#!/usr/bin/env bash
# Полный прогон: курсы → БД → расчёт → сверка с pandas. Запуск: bash run_all.sh
set -euo pipefail
cd "$(dirname "$0")"
DB=${DB:-fx}
PSQL=${PSQL:-psql}
python scripts/fetch_rates.py            # добавь --live, если есть доступ к cbr.ru
python data/generate_items.py
$PSQL -c "DROP DATABASE IF EXISTS $DB" postgres
$PSQL -c "CREATE DATABASE $DB" postgres
$PSQL -v ON_ERROR_STOP=1 -d $DB -f data/ddl.sql -f data/load.sql
for f in sql/0*.sql; do echo "== $f"; $PSQL -v ON_ERROR_STOP=1 -d $DB -f "$f"; done
python tests/check_revaluation.py
