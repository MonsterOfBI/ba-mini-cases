-- Загрузка CSV. Запускать из корня репозитория:  psql -d m8 -f data/load.sql
\copy applications FROM 'data/applications.csv' WITH (FORMAT csv, HEADER true, NULL '')
\copy app_events FROM 'data/app_events.csv' WITH (FORMAT csv, HEADER true, NULL '')
ANALYZE;
SELECT (SELECT COUNT(*) FROM applications) AS applications, (SELECT COUNT(*) FROM app_events) AS events;
