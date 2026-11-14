-- Бизнес-вопрос (AS-IS): правда ли, что напоминания уходят нерегулярно? Насколько быстро мы реагируем на просрочку?
-- Берём документы, которые были просрочены хотя бы на 1 день, и смотрим первое действие по взысканию.
-- Целевое правило TO-BE: напоминание не позже 1 рабочего дня после срока оплаты (BR-01).
WITH paid AS (
    SELECT doc_id, SUM(amount) AS paid_amount, MAX(paid_at) AS last_paid
    FROM receipts GROUP BY doc_id
),
overdue AS (                                  -- дата, когда долг закрыт (или отчётная дата, если открыт)
    SELECT s.doc_id, s.due_date,
           CASE WHEN p.paid_amount >= s.amount THEN p.last_paid ELSE DATE '2026-10-31' END AS closed_or_report
    FROM sales_docs s
    LEFT JOIN paid p ON p.doc_id = s.doc_id
    WHERE s.due_date < DATE '2026-10-31'
),
first_action AS (
    SELECT doc_id, MIN(action_at) AS first_action_at
    FROM collection_actions GROUP BY doc_id
)
SELECT COUNT(*)                                                                    AS overdue_docs,
       COUNT(fa.doc_id)                                                            AS with_any_action,
       ROUND(100.0 * COUNT(fa.doc_id) / COUNT(*), 1)                               AS pct_with_action,
       ROUND(100.0 * COUNT(*) FILTER (WHERE fa.first_action_at - o.due_date <= 1) / COUNT(*), 1) AS pct_reminded_next_day,
       PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY fa.first_action_at - o.due_date) AS median_days_to_first_action
FROM overdue o
LEFT JOIN first_action fa ON fa.doc_id = o.doc_id
WHERE o.closed_or_report > o.due_date;       -- был просрочен хотя бы день
