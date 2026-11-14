-- Бизнес-вопрос: какие курсовые разницы по каждой статье на каждую отчётную дату и при погашении?
-- Логика (BR-01, BR-04, BR-05): по каждой монетарной статье строим цепочку событий
--   признание → отчётные даты, пока статья открыта → погашение,
-- и считаем разницу между курсом события и курсом ПРЕДЫДУЩЕГО события (LAG).
CREATE OR REPLACE VIEW v_revaluation AS
WITH events AS (
    SELECT item_id, recognized_on AS event_date, 'признание' AS event_type FROM open_items WHERE is_monetary
    UNION ALL
    SELECT i.item_id, rd.report_date, 'переоценка'
    FROM open_items i JOIN reporting_dates rd
      ON rd.report_date > i.recognized_on
     AND (i.settled_on IS NULL OR rd.report_date < i.settled_on)   -- погашена в этот день → считаем как погашение
    WHERE i.is_monetary
    UNION ALL
    SELECT item_id, settled_on, 'погашение' FROM open_items WHERE is_monetary AND settled_on IS NOT NULL
),
priced AS (
    SELECT e.*, i.doc_no, i.account, i.side, i.currency, i.amount_cur, r.rate_date, r.unit_rate
    FROM events e
    JOIN open_items i USING (item_id)
    CROSS JOIN LATERAL (                                   -- курс, действующий на дату события (BR-03)
        SELECT rate_date, unit_rate FROM fx_rates r
        WHERE r.char_code = i.currency AND r.rate_date <= e.event_date
        ORDER BY r.rate_date DESC LIMIT 1
    ) r
),
chained AS (
    SELECT p.*,
           LAG(unit_rate) OVER (PARTITION BY item_id ORDER BY event_date) AS prev_rate
    FROM priced p
)
SELECT item_id, doc_no, account, side, currency, amount_cur, event_date, event_type,
       rate_date, prev_rate, unit_rate,
       round(amount_cur * unit_rate, 2)                                 AS rub_amount,
       round(amount_cur * (unit_rate - prev_rate), 2)                   AS fx_diff_balance,   -- изменение рублёвой оценки
       -- в доходах/расходах: актив подорожал → доход; обязательство подорожало → расход (BR-04)
       round(amount_cur * (unit_rate - prev_rate), 2) * CASE side WHEN 'asset' THEN 1 ELSE -1 END AS fx_result
FROM chained
WHERE prev_rate IS NOT NULL;                                -- у признания нет предыдущего курса

SELECT event_date AS дата, event_type AS событие, doc_no AS документ, currency AS вал,
       amount_cur AS сумма_в_валюте, prev_rate AS был_курс, unit_rate AS стал_курс, fx_result AS результат_руб
FROM v_revaluation
ORDER BY event_date, item_id
LIMIT 15;
