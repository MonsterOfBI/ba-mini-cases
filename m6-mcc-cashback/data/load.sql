-- Загрузка CSV. Запускать из корня репозитория:  psql -d m6 -f data/load.sql
\copy mcc_groups FROM 'data/mcc_groups.csv' WITH (FORMAT csv, HEADER true)
\copy clients FROM 'data/clients.csv' WITH (FORMAT csv, HEADER true)
\copy merchants FROM 'data/merchants.csv' WITH (FORMAT csv, HEADER true)
\copy client_categories FROM 'data/client_categories.csv' WITH (FORMAT csv, HEADER true)
\copy transactions FROM 'data/transactions.csv' WITH (FORMAT csv, HEADER true)
ANALYZE;
SELECT (SELECT COUNT(*) FROM transactions) AS tx, (SELECT COUNT(*) FROM clients) AS clients;
