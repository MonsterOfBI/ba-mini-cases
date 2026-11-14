-- Бизнес-вопрос: сколько денег «заморожено» у клиентов сверх договора и сколько стоит это замораживание?
-- Логика: каждый день DSO сверх нормы = ещё одна средняя дневная выручка, которая лежит у клиентов.
-- Норма = средневзвешенная отсрочка по договорам + 3 дня на банк и разнесение (допущение).
-- Стоимость денег — ставка, под которую компания берёт овердрафт (допущение 18 % годовых, меняйте параметр).
WITH params AS (
    SELECT DATE '2026-08-01' AS from_d, DATE '2026-10-31' AS to_d, 0.18 AS money_rate, 3 AS tech_days
),
rev AS (
    SELECT SUM(s.amount) / (p.to_d - p.from_d + 1) AS daily_revenue
    FROM sales_docs s, params p
    WHERE s.shipped_at BETWEEN p.from_d AND p.to_d
    GROUP BY p.to_d, p.from_d
),
ar AS (
    SELECT (SELECT SUM(amount) FROM sales_docs WHERE shipped_at <= p.to_d)
         - (SELECT SUM(amount) FROM receipts   WHERE paid_at    <= p.to_d) AS receivables
    FROM params p
),
norm AS (                                   -- договорная отсрочка, взвешенная по выручке клиентов
    SELECT SUM(c.payment_terms_days * s.amount) / SUM(s.amount) AS terms_days
    FROM sales_docs s JOIN customers c USING (customer_id), params p
    WHERE s.shipped_at BETWEEN p.from_d AND p.to_d
)
SELECT ROUND(ar.receivables / rev.daily_revenue, 1)                       AS dso_3m_days,
       ROUND(norm.terms_days + p.tech_days, 1)                            AS target_dso_days,
       ROUND(ar.receivables / rev.daily_revenue - norm.terms_days - p.tech_days, 1) AS excess_days,
       ROUND(rev.daily_revenue / 1e6, 2)                                  AS daily_revenue_mln,
       ROUND((ar.receivables - (norm.terms_days + p.tech_days) * rev.daily_revenue) / 1e6, 1) AS frozen_cash_mln,
       ROUND((ar.receivables - (norm.terms_days + p.tech_days) * rev.daily_revenue) * p.money_rate / 1e3) AS cost_per_year_thous
FROM ar, rev, norm, params p;
