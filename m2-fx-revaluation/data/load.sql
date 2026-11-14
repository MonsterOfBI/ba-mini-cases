-- Загрузка CSV. Запускать из корня репозитория: psql -d fx -f data/load.sql
CREATE TEMP TABLE stg_rates (requested_date date, rate_date date, char_code char(3), nominal int, value numeric, unit_rate numeric);
\copy stg_rates FROM 'data/rates.csv' WITH (FORMAT csv, HEADER true)
-- один и тот же курс мог прийти на несколько запрошенных дат (выходные) — берём уникальные
INSERT INTO fx_rates SELECT DISTINCT rate_date, char_code, nominal, value, unit_rate FROM stg_rates;
\copy open_items FROM 'data/open_items.csv' WITH (FORMAT csv, HEADER true)
SELECT (SELECT count(*) FROM fx_rates) AS rates, (SELECT count(*) FROM open_items) AS items;
