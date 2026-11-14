-- Бизнес-вопрос: как вернуть программу в бюджет 950 тыс. ₽ в месяц? Считаем «что если» на тех же операциях.
-- Сценарии: S0 как сейчас; S1 лимит 2 000 ₽; S2 АЗС 3 % вместо 5 %; S3 супермаркеты убрать из повышенных;
-- S4 = S1 + S2; S5 = S2 + S3. Расчёт повторяет логику v_purchase_cashback, но с параметрами сценария (без учёта возвратов).
WITH scenarios(code, name, cap, fuel_rate, supermarkets_electable) AS (
    VALUES ('S0', 'Как сейчас',                      3000, 0.05, TRUE),
           ('S1', 'Лимит 2 000 ₽',                   2000, 0.05, TRUE),
           ('S2', 'АЗС 3 %',                         3000, 0.03, TRUE),
           ('S3', 'Супермаркеты только 1 %',         3000, 0.05, FALSE),
           ('S4', 'Лимит 2 000 ₽ + АЗС 3 %',         2000, 0.03, TRUE),
           ('S5', 'АЗС 3 % + супермаркеты только 1 %', 3000, 0.03, FALSE)
),
base AS (
    SELECT tx_id, client_id, month, tx_date, amount, group_code, is_excluded, elevated_rate, is_chosen
    FROM v_purchase_cashback
),
calc AS (
    SELECT s.code, s.name, s.cap, b.client_id, b.month, b.tx_date, b.tx_id,
           FLOOR(b.amount * CASE
               WHEN b.is_excluded OR b.amount < 100 THEN 0
               WHEN b.is_chosen AND b.group_code = 'fuel' THEN s.fuel_rate
               WHEN b.is_chosen AND b.group_code = 'supermarkets' AND NOT s.supermarkets_electable THEN 0.01
               WHEN b.is_chosen AND b.elevated_rate IS NOT NULL THEN b.elevated_rate
               ELSE 0.01 END) AS cb
    FROM base b CROSS JOIN scenarios s
),
capped AS (
    SELECT code, name, cap, month, cb,
           SUM(cb) OVER (PARTITION BY code, client_id, month ORDER BY tx_date, tx_id) AS run
    FROM calc
)
SELECT code, name,
       ROUND(SUM(LEAST(cb, GREATEST(cap - (run - cb), 0))) / 3 / 1e3)              AS cost_per_month_thous,
       ROUND(100 * (SUM(LEAST(cb, GREATEST(cap - (run - cb), 0))) / 3 / 950000 - 1), 1) AS vs_budget_pct
FROM capped
GROUP BY code, name
ORDER BY code;
