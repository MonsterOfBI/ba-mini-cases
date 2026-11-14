-- Бизнес-вопрос: у каких клиентов платёжная дисциплина ухудшается? Это ранний сигнал до того, как долг станет 90+.
-- Для каждого платежа считаем опоздание (дата платежа − срок оплаты) и через LAG сравниваем с предыдущим
-- платежом того же клиента. Если опоздание растёт в большинстве случаев — клиент «портится».
WITH late AS (
    SELECT s.customer_id, r.paid_at,
           r.paid_at - s.due_date AS days_late
    FROM receipts r
    JOIN sales_docs s ON s.doc_id = r.doc_id
),
diffs AS (
    SELECT customer_id, paid_at, days_late,
           days_late - LAG(days_late) OVER (PARTITION BY customer_id ORDER BY paid_at) AS delta,
           paid_at   - LAG(paid_at)   OVER (PARTITION BY customer_id ORDER BY paid_at) AS days_between_payments
    FROM late
),
per_customer AS (
    SELECT customer_id,
           COUNT(*)                                               AS payments,
           ROUND(AVG(days_late) FILTER (WHERE paid_at <  DATE '2026-04-01'), 1) AS late_q1,
           ROUND(AVG(days_late) FILTER (WHERE paid_at >= DATE '2026-08-01'), 1) AS late_aug_oct,
           ROUND(AVG(days_between_payments), 1)                   AS avg_days_between_payments,
           ROUND(100.0 * COUNT(*) FILTER (WHERE delta > 0) / NULLIF(COUNT(delta), 0), 0) AS pct_worse_than_prev
    FROM diffs
    GROUP BY customer_id
)
SELECT c.name, c.sales_manager, p.payments, p.late_q1, p.late_aug_oct,
       p.late_aug_oct - p.late_q1 AS growth_days, p.avg_days_between_payments, p.pct_worse_than_prev
FROM per_customer p
JOIN customers c USING (customer_id)
WHERE p.late_aug_oct - p.late_q1 >= 10     -- опоздание выросло хотя бы на 10 дней
ORDER BY growth_days DESC;
