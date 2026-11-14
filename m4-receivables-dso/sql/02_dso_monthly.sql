-- Бизнес-вопрос: за сколько дней в среднем мы получаем деньги за отгрузку и растёт ли этот срок?
-- DSO (Days Sales Outstanding) = дебиторка на конец месяца / выручка за месяц × дней в месяце.
-- Пример: долг 30 млн, выручка за 30-дневный месяц 20 млн → DSO = 30/20×30 = 45 дней.
-- Месячный DSO «прыгает», если выручка месяца нетипична, поэтому рядом считаем DSO по 3 месяцам:
-- дебиторка / выручка за 3 месяца × дней в этих 3 месяцах (оконная SUM ... ROWS 2 PRECEDING).
-- Январь занижен: в данных нет долгов, перешедших с 2025 года (эффект старта), сравниваем с февраля.
-- Приёмы: generate_series — календарь месяцев, коррелированные подзапросы, LAG — изменение к прошлому месяцу.
WITH months AS (
    SELECT (date_trunc('month', m) + INTERVAL '1 month - 1 day')::date AS month_end,
           date_trunc('month', m)::date                                AS month_start
    FROM generate_series(DATE '2026-01-01', DATE '2026-10-01', INTERVAL '1 month') AS m
),
ar AS (                                     -- дебиторка на конец каждого месяца
    SELECT mo.month_end,
           (SELECT COALESCE(SUM(s.amount), 0) FROM sales_docs s WHERE s.shipped_at <= mo.month_end)
         - (SELECT COALESCE(SUM(r.amount), 0) FROM receipts r   WHERE r.paid_at    <= mo.month_end) AS receivables,
           (SELECT COALESCE(SUM(s.amount), 0) FROM sales_docs s
             WHERE s.shipped_at BETWEEN mo.month_start AND mo.month_end)                            AS revenue,
           mo.month_end - mo.month_start + 1                                                         AS days_in_month
    FROM months mo
),
dso AS (
    SELECT month_end, receivables, revenue,
           ROUND(receivables / NULLIF(revenue, 0) * days_in_month, 1) AS dso_days,
           ROUND(receivables
                 / NULLIF(SUM(revenue)       OVER (ORDER BY month_end ROWS 2 PRECEDING), 0)
                 *        SUM(days_in_month) OVER (ORDER BY month_end ROWS 2 PRECEDING), 1) AS dso_3m_days
    FROM ar
)
SELECT to_char(month_end, 'YYYY-MM')                 AS month,
       ROUND(receivables / 1e6, 1)                   AS receivables_mln,
       ROUND(revenue / 1e6, 1)                       AS revenue_mln,
       dso_days,
       dso_3m_days,
       dso_days - LAG(dso_days) OVER (ORDER BY month_end) AS change_vs_prev_month
FROM dso
ORDER BY month_end;
