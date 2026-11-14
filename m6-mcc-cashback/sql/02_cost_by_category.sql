-- Бизнес-вопрос: на что уходит кэшбэк и сколько мы превышаем бюджет?
-- Стоимость по группам MCC: оборот, кэшбэк, эффективная ставка, доля в расходах. Внизу — сравнение с бюджетом
-- и с доходом банка от интерчейнджа (комиссия, которую банк-эмитент получает с каждой покупки).
SELECT pc.group_code,
       ROUND(SUM(pc.amount) / 1e6, 1)                                     AS turnover_mln,
       ROUND(SUM(pc.cashback) / 1e3)                                      AS cashback_thous,
       ROUND(100 * SUM(pc.cashback) / NULLIF(SUM(pc.amount), 0), 2)       AS effective_rate_pct,
       ROUND(100 * SUM(pc.cashback) / SUM(SUM(pc.cashback)) OVER (), 1)   AS share_of_cost_pct,
       ROUND(100.0 * COUNT(*) FILTER (WHERE pc.rule_applied LIKE 'CB-03%') / COUNT(*), 1) AS pct_tx_elevated
FROM v_purchase_cashback pc
GROUP BY pc.group_code
ORDER BY cashback_thous DESC;

WITH p AS (
    SELECT MAX(value) FILTER (WHERE param = 'budget_month')     AS budget,
           MAX(value) FILTER (WHERE param = 'interchange_rate') AS ich
    FROM program_params
)
SELECT to_char(m.month, 'YYYY-MM')                                  AS month,
       ROUND(SUM(m.net_cashback) / 1e3)                             AS cost_thous,
       ROUND(p.budget / 1e3)                                        AS budget_thous,
       ROUND(100 * (SUM(m.net_cashback) / p.budget - 1), 1)         AS over_budget_pct,
       ROUND(SUM(m.turnover) * p.ich / 1e3)                         AS interchange_income_thous,
       ROUND((SUM(m.turnover) * p.ich - SUM(m.net_cashback)) / 1e3) AS margin_thous
FROM v_client_month m CROSS JOIN p
GROUP BY m.month, p.budget, p.ich
ORDER BY m.month;
