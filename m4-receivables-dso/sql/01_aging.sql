-- Бизнес-вопрос: сколько нам должны на отчётную дату и насколько долг «состарился»?
-- Aging (старение дебиторки) = остаток долга по каждой реализации, разложенный по корзинам дней просрочки.
-- Приёмы: CTE (WITH) по шагам, LEFT JOIN — чтобы не потерять неоплаченные документы, CASE — корзины.
WITH params AS (
    SELECT DATE '2026-10-31' AS report_date
),
paid AS (                                   -- сколько оплачено по документу на отчётную дату
    SELECT r.doc_id, SUM(r.amount) AS paid_amount
    FROM receipts r, params p
    WHERE r.paid_at <= p.report_date
    GROUP BY r.doc_id
),
open_docs AS (                              -- остаток долга по каждому документу
    SELECT s.doc_id, s.customer_id, s.due_date,
           s.amount - COALESCE(pd.paid_amount, 0) AS balance,
           p.report_date - s.due_date             AS days_overdue
    FROM sales_docs s
    CROSS JOIN params p
    LEFT JOIN paid pd ON pd.doc_id = s.doc_id
    WHERE s.shipped_at <= p.report_date
      AND s.amount - COALESCE(pd.paid_amount, 0) > 0
),
bucketed AS (
    SELECT *,
           CASE
               WHEN days_overdue <= 0  THEN '0. В срок'
               WHEN days_overdue <= 30 THEN '1. 1–30 дней'
               WHEN days_overdue <= 60 THEN '2. 31–60 дней'
               WHEN days_overdue <= 90 THEN '3. 61–90 дней'
               ELSE                         '4. 90+ дней'
           END AS bucket
    FROM open_docs
)
SELECT bucket,
       COUNT(*)                                                      AS docs,
       COUNT(DISTINCT customer_id)                                   AS customers,
       ROUND(SUM(balance) / 1000, 0)                                 AS balance_thous_rub,
       ROUND(100.0 * SUM(balance) / (SELECT SUM(balance) FROM open_docs), 1) AS share_pct
       -- Ловушка: SUM(SUM(balance)) OVER () здесь дал бы 50 %, потому что ROLLUP добавляет строку итога
FROM bucketed
GROUP BY ROLLUP (bucket)                    -- последняя строка (NULL) = вся дебиторка
ORDER BY bucket NULLS LAST;
