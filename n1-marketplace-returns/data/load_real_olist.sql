-- Загрузка настоящего датасета Olist (скачай с Kaggle: "Brazilian E-Commerce Public Dataset by Olist")
-- Запуск из папки с CSV:  psql -d olist -f ddl_olist.sql -f load_real_olist.sql
\copy customers     FROM 'olist_customers_dataset.csv'     CSV HEADER
\copy sellers       FROM 'olist_sellers_dataset.csv'       CSV HEADER
\copy orders        FROM 'olist_orders_dataset.csv'        CSV HEADER
\copy order_items   FROM 'olist_order_items_dataset.csv'   CSV HEADER
\copy order_reviews FROM 'olist_order_reviews_dataset.csv' CSV HEADER
