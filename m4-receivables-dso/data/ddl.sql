-- Схема данных кейса «Дебиторка: напоминания, aging и DSO» (PostgreSQL 16).
-- ООО «Ромашка-Опт» (вымышленная) отгружает товар магазинам с отсрочкой платежа.
DROP TABLE IF EXISTS collection_actions, receipts, sales_docs, customers CASCADE;

CREATE TABLE customers (
    customer_id        INT PRIMARY KEY,
    name               TEXT NOT NULL,
    inn                VARCHAR(12) NOT NULL UNIQUE,
    segment            TEXT NOT NULL CHECK (segment IN ('сеть', 'магазин', 'HoReCa')),
    payment_terms_days INT NOT NULL CHECK (payment_terms_days > 0),   -- отсрочка по договору
    credit_limit       NUMERIC(14,2) NOT NULL,                          -- лимит дебиторки на клиента
    sales_manager      TEXT NOT NULL
);

-- Реализация (УПД): отгрузка, после которой у клиента появляется долг
CREATE TABLE sales_docs (
    doc_id      INT PRIMARY KEY,
    customer_id INT NOT NULL REFERENCES customers,
    doc_no      TEXT NOT NULL UNIQUE,
    shipped_at  DATE NOT NULL,
    due_date    DATE NOT NULL CHECK (due_date >= shipped_at),
    amount      NUMERIC(14,2) NOT NULL CHECK (amount > 0)            -- с НДС 22 %
);

-- Поступления от клиента; одна реализация может оплачиваться несколькими платежами (частичная оплата)
CREATE TABLE receipts (
    receipt_id  INT PRIMARY KEY,
    doc_id      INT NOT NULL REFERENCES sales_docs,
    paid_at     DATE NOT NULL,
    amount      NUMERIC(14,2) NOT NULL CHECK (amount > 0)
);

-- Действия по взысканию: что и когда делали с просроченным долгом
CREATE TABLE collection_actions (
    action_id   INT PRIMARY KEY,
    doc_id      INT NOT NULL REFERENCES sales_docs,
    action_type TEXT NOT NULL CHECK (action_type IN ('reminder', 'call', 'stop_shipments', 'claim', 'lawsuit')),
    action_at   DATE NOT NULL,
    performed_by TEXT NOT NULL
);

CREATE INDEX ON sales_docs (customer_id, due_date);
CREATE INDEX ON receipts (doc_id, paid_at);
CREATE INDEX ON collection_actions (doc_id, action_at);
