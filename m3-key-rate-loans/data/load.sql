-- Загрузка CSV. Запускать из корня репозитория: psql -d loans -f data/load.sql
\copy key_rate FROM 'data/key_rate.csv' WITH (FORMAT csv, HEADER true)
\copy loans FROM 'data/loans.csv' WITH (FORMAT csv, HEADER true)
SELECT (SELECT count(*) FROM key_rate) AS key_rate_days, (SELECT count(*) FROM loans) AS loans;
