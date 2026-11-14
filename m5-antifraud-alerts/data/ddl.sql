-- Схема данных кейса «Разбор антифрод-алертов» (PostgreSQL 16).
-- Учебный банк «Пример» (вымышленный), мобильный кошелёк. Таблица transactions повторяет колонки PaySim.
DROP TABLE IF EXISTS alert_decisions, alert_rule_hits, alerts, alert_rules, transactions CASCADE;

CREATE TABLE transactions (
    tx_id           BIGSERIAL PRIMARY KEY,
    step            INT NOT NULL,              -- номер часа от начала периода (1 = первый час 1-го дня)
    type            TEXT NOT NULL CHECK (type IN ('PAYMENT','TRANSFER','CASH_OUT','CASH_IN','DEBIT')),
    amount          NUMERIC(14,2) NOT NULL,
    name_orig       TEXT NOT NULL,             -- кто платит
    oldbalance_org  NUMERIC(14,2),
    newbalance_orig NUMERIC(14,2),
    name_dest       TEXT NOT NULL,             -- кому платят (C… клиент, M… магазин)
    oldbalance_dest NUMERIC(14,2),
    newbalance_dest NUMERIC(14,2),
    is_fraud        SMALLINT NOT NULL,         -- разметка «правды»: 1 = мошенническая операция
    is_flagged_fraud SMALLINT NOT NULL         -- флаг старого правила из PaySim (у нас не используется)
);

-- Каталог правил: что ловим, почему, какой вес даёт правило в итоговом балле
CREATE TABLE alert_rules (
    rule_code   TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    description TEXT NOT NULL,
    weight      INT NOT NULL CHECK (weight BETWEEN 1 AND 100),
    owner       TEXT NOT NULL
);

-- Алерт = подозрительная операция. Одна операция → максимум один алерт, даже если сработало несколько правил
CREATE TABLE alerts (
    alert_id    BIGSERIAL PRIMARY KEY,
    tx_id       BIGINT NOT NULL UNIQUE REFERENCES transactions,
    created_step INT NOT NULL,
    score       INT NOT NULL,                  -- сумма весов сработавших правил, максимум 100
    route_as_is TEXT NOT NULL DEFAULT 'analyst',
    route_to_be TEXT NOT NULL CHECK (route_to_be IN ('auto_block','sms_confirm','analyst','monitor'))
);

CREATE TABLE alert_rule_hits (                 -- какие правила сработали в алерте (многие-ко-многим)
    alert_id  BIGINT REFERENCES alerts,
    rule_code TEXT REFERENCES alert_rules,
    PRIMARY KEY (alert_id, rule_code)
);

-- Итог разбора (TO-BE): кто решил, что решил, сколько минут это заняло
CREATE TABLE alert_decisions (
    alert_id     BIGINT PRIMARY KEY REFERENCES alerts,
    decided_by   TEXT NOT NULL CHECK (decided_by IN ('system','client','analyst','none')),
    decision     TEXT NOT NULL CHECK (decision IN ('blocked','released','monitored')),
    minutes_to_decision INT NOT NULL,
    is_true_positive BOOLEAN NOT NULL
);

CREATE INDEX ON transactions (name_orig, step);
CREATE INDEX ON transactions (name_dest, step);
