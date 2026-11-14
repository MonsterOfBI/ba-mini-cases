-- Схема публичного датасета Olist (Brazilian E-Commerce Public Dataset, Kaggle, CC BY-NC-SA 4.0).
-- Имена таблиц и колонок как в CSV-файлах датасета. Нужны 5 из 9 файлов.
DROP TABLE IF EXISTS order_reviews, order_items, orders, customers, sellers CASCADE;
CREATE TABLE customers (
    customer_id TEXT PRIMARY KEY, customer_unique_id TEXT, customer_zip_code_prefix TEXT,
    customer_city TEXT, customer_state TEXT);
CREATE TABLE sellers (
    seller_id TEXT PRIMARY KEY, seller_zip_code_prefix TEXT, seller_city TEXT, seller_state TEXT);
CREATE TABLE orders (
    order_id TEXT PRIMARY KEY, customer_id TEXT REFERENCES customers, order_status TEXT,
    order_purchase_timestamp TIMESTAMP, order_approved_at TIMESTAMP,
    order_delivered_carrier_date TIMESTAMP, order_delivered_customer_date TIMESTAMP,
    order_estimated_delivery_date TIMESTAMP);
CREATE TABLE order_items (
    order_id TEXT REFERENCES orders, order_item_id INT, product_id TEXT, seller_id TEXT REFERENCES sellers,
    shipping_limit_date TIMESTAMP, price NUMERIC(10,2), freight_value NUMERIC(10,2),
    PRIMARY KEY (order_id, order_item_id));
CREATE TABLE order_reviews (
    review_id TEXT, order_id TEXT REFERENCES orders, review_score INT,
    review_comment_title TEXT, review_comment_message TEXT,
    review_creation_date TIMESTAMP, review_answer_timestamp TIMESTAMP);
