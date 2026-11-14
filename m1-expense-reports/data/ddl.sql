-- Модель данных авансовых отчётов (учебная, PostgreSQL)
CREATE TABLE employees (
    employee_id SERIAL PRIMARY KEY,
    full_name   TEXT NOT NULL,
    manager_id  INT REFERENCES employees
);
CREATE TABLE trips (
    trip_id     SERIAL PRIMARY KEY,
    employee_id INT  NOT NULL REFERENCES employees,
    city        TEXT NOT NULL,
    date_from   DATE NOT NULL,
    date_to     DATE NOT NULL CHECK (date_to >= date_from),
    advance_amount NUMERIC(12,2) NOT NULL DEFAULT 0   -- выданный аванс
);
CREATE TABLE expense_reports (
    report_id   SERIAL PRIMARY KEY,
    trip_id     INT  NOT NULL UNIQUE REFERENCES trips,  -- один отчёт на командировку
    status      TEXT NOT NULL CHECK (status IN ('draft','on_approval','approved','returned','posted','paid')),
    submitted_at TIMESTAMP,
    approved_at  TIMESTAMP,
    paid_at      TIMESTAMP
);
CREATE TABLE expenses (
    expense_id  SERIAL PRIMARY KEY,
    report_id   INT  NOT NULL REFERENCES expense_reports ON DELETE CASCADE,
    category    TEXT NOT NULL CHECK (category IN ('hotel','taxi','ticket','per_diem','alcohol','other')),
    amount      NUMERIC(12,2) NOT NULL CHECK (amount > 0),
    spent_at    TIMESTAMP NOT NULL,
    receipt_qr  TEXT,                                  -- строка QR чека: t=...&s=...&fn=...&i=...&fp=...
    fns_checked BOOLEAN NOT NULL DEFAULT FALSE,
    policy_result TEXT CHECK (policy_result IN ('ok','over_limit','forbidden')),
    explanation TEXT                                   -- обязательно при over_limit (проверяется в приложении)
);
-- Итог отчёта: к выплате = сумма разрешённых расходов + суточные − аванс (может быть отрицательным: вернуть в кассу)
