-- Загрузка операций. Запускать из корня репозитория:  psql -d m5 -f data/load.sql
-- Для настоящего PaySim замените путь на свой CSV (колонки и порядок те же).
\copy transactions (step, type, amount, name_orig, oldbalance_org, newbalance_orig, name_dest, oldbalance_dest, newbalance_dest, is_fraud, is_flagged_fraud) FROM 'data/transactions.csv' WITH (FORMAT csv, HEADER true)
ANALYZE transactions;
SELECT COUNT(*) AS tx, SUM(is_fraud) AS fraud_tx FROM transactions;
