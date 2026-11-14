-- Бизнес-вопрос: кто «съедает» бюджет? Сколько клиентов упирается в лимит и как выбор категорий влияет на стоимость.
-- 1) Распределение клиентов по месячному кэшбэку и сколько сэкономил лимит 3 000 ₽.
WITH buckets AS (
    SELECT *, CASE WHEN accrued >= 3000 THEN '4. лимит 3 000'
                   WHEN accrued >= 1500 THEN '3. 1 500–2 999'
                   WHEN accrued >= 500  THEN '2. 500–1 499'
                   ELSE                      '1. до 500' END AS bucket
    FROM v_client_month
)
SELECT bucket,
       COUNT(*)                                                         AS client_months,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)               AS share_pct,
       ROUND(SUM(accrued) / 3 / 1e3)                                    AS cashback_per_month_thous,
       ROUND(100 * SUM(accrued) / SUM(SUM(accrued)) OVER (), 1)         AS share_of_cost_pct,
       ROUND(SUM(cashback_raw - accrued) / 3 / 1e3)                     AS saved_by_cap_per_month_thous
FROM buckets
GROUP BY bucket
ORDER BY bucket;

-- 2) «Умные» клиенты (выбирают категории, где тратят больше всего) против выбирающих наугад
SELECT CASE WHEN c.is_smart_chooser THEN 'выбирает по своим тратам' ELSE 'выбирает наугад' END AS chooser,
       COUNT(DISTINCT c.client_id)                                  AS clients,
       ROUND(SUM(m.turnover) / COUNT(*) )                           AS avg_turnover_per_month,
       ROUND(SUM(m.net_cashback) / COUNT(*))                        AS avg_cashback_per_month,
       ROUND(100 * SUM(m.net_cashback) / SUM(m.turnover), 2)        AS effective_rate_pct
FROM v_client_month m JOIN clients c USING (client_id)
GROUP BY 1;
