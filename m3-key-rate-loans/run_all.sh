#!/usr/bin/env bash
# Полный прогон: ставка ЦБ → БД → расчёт. Запуск: bash run_all.sh
set -euo pipefail
cd "$(dirname "$0")"
DB=${DB:-loans}
python scripts/fetch_key_rate.py          # добавь --live, если есть доступ к cbr.ru
python data/generate_portfolio.py
psql -c "DROP DATABASE IF EXISTS $DB" postgres
psql -c "CREATE DATABASE $DB" postgres
psql -v ON_ERROR_STOP=1 -d $DB -f data/ddl.sql -f data/load.sql
for f in sql/0*.sql; do echo "== $f"; psql -v ON_ERROR_STOP=1 -d $DB -f "$f"; done
