-- Бизнес-вопрос: какая ставка и сколько процентов по каждому кредиту в каждом месяце?
-- Правила: BR-01 ставка = КС + маржа; BR-02 пол и потолок; BR-03 КС берётся на дату фиксации;
-- BR-04 округление до 0,01 п.п.; BR-05 проценты = остаток × ставка × дни / 365.
CREATE OR REPLACE VIEW v_loan_month AS
WITH months AS (
    SELECT m::date AS period_start, (m + interval '1 month')::date AS period_end
    FROM generate_series(date '2025-01-01', date '2026-12-01', interval '1 month') m
),
fix AS (
    SELECT mo.*, (mo.period_start - p.lookback_days) AS fixing_date, kr.key_rate
    FROM months mo
    CROSS JOIN rate_params p
    CROSS JOIN LATERAL (
        SELECT key_rate FROM key_rate WHERE rate_date <= mo.period_start - p.lookback_days
        ORDER BY rate_date DESC LIMIT 1
    ) kr
),
lm AS (
    SELECT l.*, f.period_start, f.period_end, f.fixing_date, f.key_rate,
           -- сколько месяцев прошло с выдачи → линейное погашение долга
           (extract(year FROM age(f.period_start, l.issue_date)) * 12 + extract(month FROM age(f.period_start, l.issue_date)))::int AS month_no
    FROM loans l JOIN fix f
      ON f.period_start >= l.issue_date
     AND f.period_start < l.issue_date + make_interval(months => l.term_months)
)
SELECT loan_id, contract_no, client, segment, notify_channel, period_start, fixing_date, key_rate, margin_pp, floor_pct, cap_pct,
       key_rate + margin_pp                                                     AS raw_rate,
       round(LEAST(GREATEST(key_rate + margin_pp, COALESCE(floor_pct, 0)), COALESCE(cap_pct, 999)), 2) AS applied_rate,
       (floor_pct IS NOT NULL AND key_rate + margin_pp < floor_pct)             AS at_floor,
       (cap_pct   IS NOT NULL AND key_rate + margin_pp > cap_pct)               AS at_cap,
       round(principal * (1 - month_no::numeric / term_months), 2)             AS balance,
       (period_end - period_start)                                             AS days
FROM lm;

CREATE OR REPLACE VIEW v_loan_interest AS
SELECT v.*,
       round(balance * applied_rate / 100 * days / 365, 2)      AS interest,
       round(balance * raw_rate     / 100 * days / 365, 2)      AS interest_no_limits   -- «как было бы без пола и потолка»
FROM v_loan_month v;

SELECT contract_no AS договор, period_start AS период, key_rate AS кс, margin_pp AS маржа,
       floor_pct AS пол, cap_pct AS потолок, applied_rate AS ставка, at_floor AS упёрлась_в_пол, interest AS проценты
FROM v_loan_interest
WHERE loan_id = (SELECT min(loan_id) FROM loans WHERE floor_pct IS NOT NULL AND cap_pct IS NOT NULL)
ORDER BY period_start;
