-- Бизнес-вопрос (TO-BE): что каждому сотруднику сделать сегодня? Это «рабочий список», который процесс
-- генерирует каждое утро по правилам BR-01…BR-05 (см. docs/requirements.md).
-- Шаг взыскания определяется днями просрочки: 1+ → напоминание, 8+ → звонок, 22+ → стоп отгрузок,
-- 31+ → претензия, претензия старше 30 дней → иск. ROW_NUMBER оставляет топ-3 долга на каждого сотрудника.
WITH params AS (SELECT DATE '2026-10-31' AS today),
paid AS (
    SELECT doc_id, SUM(amount) AS paid_amount FROM receipts GROUP BY doc_id
),
open_overdue AS (
    SELECT s.doc_id, s.doc_no, s.customer_id,
           s.amount - COALESCE(p.paid_amount, 0) AS balance,
           pr.today - s.due_date                 AS days_overdue
    FROM sales_docs s
    CROSS JOIN params pr
    LEFT JOIN paid p ON p.doc_id = s.doc_id
    WHERE s.amount - COALESCE(p.paid_amount, 0) > 0
      AND s.due_date < pr.today
),
claims AS (
    SELECT doc_id, MIN(action_at) AS claim_at FROM collection_actions WHERE action_type = 'claim' GROUP BY doc_id
),
next_step AS (
    SELECT o.*, c.name AS customer, c.sales_manager,
           CASE
               WHEN cl.claim_at IS NOT NULL AND (SELECT today FROM params) - cl.claim_at > 30 THEN '5. Иск в арбитраж'
               WHEN cl.claim_at IS NOT NULL THEN '4. Ждём ответ на претензию'
               WHEN o.days_overdue > 30     THEN '4. Направить претензию'
               WHEN o.days_overdue > 21     THEN '3. Стоп отгрузок'
               WHEN o.days_overdue > 7      THEN '2. Звонок клиенту'
               ELSE                              '1. Напоминание'
           END AS step
    FROM open_overdue o
    JOIN customers c  ON c.customer_id = o.customer_id
    LEFT JOIN claims cl ON cl.doc_id = o.doc_id
),
owner AS (
    SELECT *,
           CASE WHEN step LIKE '1.%' THEN 'Система (авто)'
                WHEN step LIKE '2.%' THEN 'Кредит-контролёр'
                WHEN step LIKE '3.%' THEN sales_manager
                ELSE 'Юрист' END AS responsible
    FROM next_step
),
ranked AS (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY step ORDER BY balance DESC) AS rn,
           COUNT(*)    OVER (PARTITION BY step)                          AS docs_in_step,
           SUM(balance) OVER (PARTITION BY step)                         AS step_balance
    FROM owner
)
SELECT step, responsible, docs_in_step, ROUND(step_balance / 1000) AS step_balance_thous,
       rn AS top, doc_no, customer, ROUND(balance) AS balance, days_overdue
FROM ranked
WHERE rn <= 3
ORDER BY step, rn;
