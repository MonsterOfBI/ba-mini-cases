-- Модель данных переоценки (PostgreSQL 16)
DROP TABLE IF EXISTS fx_rates, open_items, reporting_dates CASCADE;

-- Курсы ЦБ: одна строка = валюта на дату установления курса
CREATE TABLE fx_rates (
    rate_date   date          NOT NULL,
    char_code   char(3)       NOT NULL,
    nominal     int           NOT NULL CHECK (nominal > 0),
    value       numeric(14,4) NOT NULL,             -- курс за nominal единиц, как в XML
    unit_rate   numeric(16,6) NOT NULL,             -- курс за 1 единицу = value / nominal
    PRIMARY KEY (rate_date, char_code)
);

-- Реестр валютных статей (выгрузка из учётной системы)
CREATE TABLE open_items (
    item_id       int PRIMARY KEY,
    doc_no        text          NOT NULL,
    item_type     text          NOT NULL CHECK (item_type IN ('payable','receivable','advance_paid','advance_received')),
    account       text          NOT NULL,           -- счёт учёта: 60.21, 62.21, 60.22, 62.22
    is_monetary   boolean       NOT NULL,           -- монетарная статья → переоценивается (BR-02)
    side          text          NOT NULL CHECK (side IN ('asset','liability')),
    counterparty  text          NOT NULL,
    currency      char(3)       NOT NULL,
    amount_cur    numeric(16,2) NOT NULL CHECK (amount_cur > 0),
    recognized_on date          NOT NULL,           -- дата признания (поставка/отгрузка)
    settled_on    date,                             -- дата погашения, NULL = открыта
    CHECK (settled_on IS NULL OR settled_on >= recognized_on)
);

-- Отчётные даты: последнее число каждого месяца (BR-01)
CREATE TABLE reporting_dates (report_date date PRIMARY KEY);
INSERT INTO reporting_dates VALUES ('2026-09-30'), ('2026-10-31');
