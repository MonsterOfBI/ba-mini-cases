-- Модель данных пересчёта плавающих ставок (PostgreSQL 16)
DROP TABLE IF EXISTS key_rate, loans, rate_params CASCADE;

-- Ключевая ставка ЦБ: одна строка на рабочий день (как отдаёт KeyRateXML)
CREATE TABLE key_rate (
    rate_date date PRIMARY KEY,
    key_rate  numeric(5,2) NOT NULL CHECK (key_rate >= 0)
);

-- Кредитный портфель (выгрузка из АБС)
CREATE TABLE loans (
    loan_id        int PRIMARY KEY,
    contract_no    text NOT NULL UNIQUE,
    client         text NOT NULL,
    segment        text NOT NULL,
    issue_date     date NOT NULL,
    term_months    int  NOT NULL CHECK (term_months > 0),
    principal      numeric(16,2) NOT NULL CHECK (principal > 0),
    margin_pp      numeric(5,2)  NOT NULL,          -- маржа над ключевой ставкой, п.п.
    floor_pct      numeric(5,2),                    -- пол ставки, NULL = нет
    cap_pct        numeric(5,2),                    -- потолок ставки, NULL = нет
    notify_channel text NOT NULL,
    CHECK (floor_pct IS NULL OR cap_pct IS NULL OR cap_pct > floor_pct)
);

-- Параметры правил (BR-03): за сколько дней до начала периода фиксируем ставку
CREATE TABLE rate_params (lookback_days int NOT NULL, min_notice_days int NOT NULL);
INSERT INTO rate_params VALUES (10, 7);
