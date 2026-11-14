-- Схема данных кейса «Кэшбэк по категориям MCC» (PostgreSQL 16). Банк «Пример» вымышленный.
DROP TABLE IF EXISTS transactions, client_categories, merchants, clients, mcc_groups, program_params CASCADE;

-- Параметры программы: меняются чаще правил, поэтому лежат в таблице, а не в коде
CREATE TABLE program_params (
    param       TEXT PRIMARY KEY,
    value       NUMERIC NOT NULL,
    description TEXT NOT NULL
);

-- Справочник MCC → группа кэшбэка (тот же, что в DMN bpmn/cashback-rate.dmn; проверяет tests/test_rules.py)
CREATE TABLE mcc_groups (
    mcc           INT PRIMARY KEY CHECK (mcc BETWEEN 0 AND 9999),
    group_code    TEXT NOT NULL,
    group_name    TEXT NOT NULL,
    elevated_rate NUMERIC(4,3),             -- NULL: категорию нельзя выбрать повышенной
    is_excluded   BOOLEAN NOT NULL          -- TRUE: кэшбэк не начисляется
);

CREATE TABLE clients (
    client_id        INT PRIMARY KEY,
    full_name        TEXT NOT NULL,          -- синтетика (Faker), реальных людей нет
    city             TEXT NOT NULL,
    spend_level      NUMERIC(5,2) NOT NULL,
    is_driver        BOOLEAN NOT NULL,
    is_smart_chooser BOOLEAN NOT NULL
);

CREATE TABLE merchants (
    merchant_id   INT PRIMARY KEY,
    merchant_name TEXT NOT NULL,
    mcc           INT NOT NULL REFERENCES mcc_groups,  -- MCC присваивает эквайер, банк-эмитент его только видит
    group_code    TEXT NOT NULL                        -- «настоящая» категория бизнеса (для поиска несоответствий)
);

-- Повышенные категории, которые клиент выбрал на месяц (максимум 2)
CREATE TABLE client_categories (
    client_id  INT REFERENCES clients,
    month      DATE NOT NULL,
    group_code TEXT NOT NULL,
    PRIMARY KEY (client_id, month, group_code)
);

CREATE TABLE transactions (
    tx_id          INT PRIMARY KEY,
    client_id      INT NOT NULL REFERENCES clients,
    merchant_id    INT NOT NULL REFERENCES merchants,
    mcc            INT NOT NULL REFERENCES mcc_groups,
    tx_date        DATE NOT NULL,
    amount         NUMERIC(12,2) NOT NULL,          -- покупка > 0, возврат < 0
    tx_type        TEXT NOT NULL CHECK (tx_type IN ('purchase', 'refund')),
    original_tx_id INT REFERENCES transactions,     -- для возврата: какая покупка возвращается
    CHECK ((tx_type = 'purchase' AND amount > 0 AND original_tx_id IS NULL)
        OR (tx_type = 'refund'   AND amount < 0 AND original_tx_id IS NOT NULL))
);
CREATE INDEX ON transactions (client_id, tx_date);

INSERT INTO program_params VALUES
 ('base_rate',        0.01,    'Базовый кэшбэк на все покупки, кроме исключённых MCC'),
 ('monthly_cap',      3000,    'Максимум кэшбэка на клиента в месяц, ₽'),
 ('min_amount',       100,     'Минимальная сумма покупки для кэшбэка, ₽'),
 ('max_categories',   2,       'Сколько повышенных категорий клиент выбирает на месяц'),
 ('budget_month',     950000,  'Бюджет программы на месяц, ₽ (утверждён на 2026 год)'),
 ('interchange_rate', 0.012,   'Средний доход банка-эмитента с покупки (интерчейндж), допущение');
