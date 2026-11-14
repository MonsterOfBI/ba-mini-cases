-- Шаг 1. Расчёт кэшбэка по правилам программы. Создаёт представления, на которых работают запросы 02–06.
-- Порядок правил (тот же, что в DMN bpmn/cashback-rate.dmn и в docs/rules.md):
--   CB-01 исключённый MCC → 0;  CB-02 покупка < 100 ₽ → 0;  CB-03 выбранная повышенная категория → её ставка;
--   CB-04 иначе базовые 1 %;  CB-05 кэшбэк округляется вниз до рубля;  CB-06 не больше 3 000 ₽ на клиента в месяц;
--   CB-07 возврат покупки списывает начисленный за неё кэшбэк в месяце возврата.
-- Лимит считаем оконной суммой: «сколько уже начислено до этой покупки» и обрезаем остаток до лимита.
CREATE OR REPLACE VIEW v_params AS
SELECT MAX(value) FILTER (WHERE param = 'base_rate')   AS base_rate,
       MAX(value) FILTER (WHERE param = 'monthly_cap') AS monthly_cap,
       MAX(value) FILTER (WHERE param = 'min_amount')  AS min_amount
FROM program_params;

CREATE OR REPLACE VIEW v_purchase_cashback AS
WITH purchases AS (
    SELECT t.tx_id, t.client_id, t.tx_date, date_trunc('month', t.tx_date)::date AS month,
           t.amount, t.mcc, g.group_code, g.is_excluded, g.elevated_rate,
           EXISTS (SELECT 1 FROM client_categories cc
                    WHERE cc.client_id = t.client_id AND cc.group_code = g.group_code
                      AND cc.month = date_trunc('month', t.tx_date)::date) AS is_chosen
    FROM transactions t
    JOIN mcc_groups g ON g.mcc = t.mcc
    WHERE t.tx_type = 'purchase'
),
rated AS (
    SELECT p.*,
           CASE
               WHEN p.is_excluded                          THEN 0
               WHEN p.amount < pr.min_amount               THEN 0
               WHEN p.is_chosen AND p.elevated_rate IS NOT NULL THEN p.elevated_rate
               ELSE pr.base_rate
           END AS rate,
           CASE
               WHEN p.is_excluded            THEN 'CB-01 исключённый MCC'
               WHEN p.amount < pr.min_amount THEN 'CB-02 покупка меньше 100 ₽'
               WHEN p.is_chosen AND p.elevated_rate IS NOT NULL THEN 'CB-03 повышенная категория'
               ELSE 'CB-04 базовая ставка'
           END AS rule_applied
    FROM purchases p CROSS JOIN v_params pr
),
raw AS (
    SELECT *, FLOOR(amount * rate) AS cashback_raw          -- CB-05: вниз до рубля
    FROM rated
),
running AS (
    SELECT *, SUM(cashback_raw) OVER (PARTITION BY client_id, month ORDER BY tx_date, tx_id) AS running_raw
    FROM raw
)
SELECT r.*,
       LEAST(r.cashback_raw, GREATEST(pr.monthly_cap - (r.running_raw - r.cashback_raw), 0)) AS cashback   -- CB-06
FROM running r CROSS JOIN v_params pr;

-- Итог по клиенту и месяцу: начислено за покупки, списано за возвраты (CB-07), к выплате
CREATE OR REPLACE VIEW v_client_month AS
WITH accrued AS (
    SELECT client_id, month, SUM(amount) AS turnover, SUM(cashback_raw) AS cashback_raw, SUM(cashback) AS accrued
    FROM v_purchase_cashback GROUP BY client_id, month
),
reversed AS (
    SELECT r.client_id, date_trunc('month', r.tx_date)::date AS month, SUM(pc.cashback) AS reversed
    FROM transactions r
    JOIN v_purchase_cashback pc ON pc.tx_id = r.original_tx_id
    WHERE r.tx_type = 'refund'
    GROUP BY r.client_id, date_trunc('month', r.tx_date)::date
)
SELECT a.client_id, a.month, a.turnover, a.cashback_raw, a.accrued,
       COALESCE(rv.reversed, 0)              AS reversed,
       a.accrued - COALESCE(rv.reversed, 0)  AS net_cashback
FROM accrued a
LEFT JOIN reversed rv ON rv.client_id = a.client_id AND rv.month = a.month;

-- Контрольный итог по месяцам
SELECT to_char(month, 'YYYY-MM')                AS month,
       ROUND(SUM(turnover) / 1e6, 1)            AS turnover_mln,
       ROUND(SUM(accrued) / 1e3)                AS accrued_thous,
       ROUND(SUM(reversed) / 1e3)               AS reversed_thous,
       ROUND(SUM(net_cashback) / 1e3)           AS net_thous,
       ROUND(100 * SUM(net_cashback) / SUM(turnover), 2) AS effective_rate_pct
FROM v_client_month
GROUP BY ROLLUP (month)
ORDER BY month NULLS LAST;
