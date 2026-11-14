-- Бизнес-вопрос (AS-IS): почему аналитики «тонут» и сколько мошенничества мы не успеваем остановить?
-- Как сейчас: операция проходит сразу, каждый алерт разбирает аналитик. Аналитик один, работает с 09:00 до 21:00,
-- разбор занимает 12 минут. Ночные алерты ждут утра. Мошенничество «остановлено», только если аналитик
-- заблокировал кошелёк дропа раньше, чем тот вывел деньги (CASH_OUT).
-- Трюк с очередью: время окончания i-го разбора = 12·i + MAX по j ≤ i (поступление_j − 12·(j−1)),
-- это бегущий максимум, его считает оконная MAX() OVER. Очередь не переносится между днями (упрощение).
WITH params AS (SELECT 12 AS handle_min),
arrivals AS (
    SELECT a.alert_id, t.tx_id, t.is_fraud, t.amount, t.type, t.name_dest,
           (t.step - 1) * 60 + ABS(hashtext(t.tx_id::text)) % 60 AS created_min      -- минута от начала периода
    FROM alerts a JOIN transactions t USING (tx_id)
),
available AS (                                  -- когда алерт может взять аналитик (рабочее окно 09:00–21:00)
    SELECT *,
           CASE
               WHEN created_min % 1440 <  540 THEN created_min - created_min % 1440 + 540          -- ночь → 09:00 этого дня
               WHEN created_min % 1440 >= 1260 THEN created_min - created_min % 1440 + 1440 + 540  -- вечер → 09:00 завтра
               ELSE created_min
           END AS avail_min
    FROM arrivals
),
queued AS (
    SELECT *, avail_min / 1440 AS work_day,
           ROW_NUMBER() OVER (PARTITION BY avail_min / 1440 ORDER BY avail_min, alert_id) AS pos
    FROM available
),
finished AS (
    SELECT q.*,
           p.handle_min * pos
           + MAX(avail_min - p.handle_min * (pos - 1)) OVER (PARTITION BY work_day ORDER BY pos) AS done_min
    FROM queued q, params p
),
cashout AS (                                    -- когда дроп вывел деньги по мошенническому переводу
    SELECT f.alert_id,
           (SELECT MIN((c.step - 1) * 60 + ABS(hashtext(c.tx_id::text)) % 60)
              FROM transactions c
             WHERE c.type = 'CASH_OUT' AND c.name_orig = f.name_dest AND c.is_fraud = 1) AS cashout_min
    FROM finished f WHERE f.is_fraud = 1 AND f.type = 'TRANSFER'
)
SELECT COUNT(*)                                                           AS alerts,
       ROUND(COUNT(*) / 30.0, 1)                                          AS alerts_per_day,
       ROUND(COUNT(*) * 12 / 60.0 / 30, 1)                                AS analyst_hours_per_day,
       ROUND(100.0 * COUNT(*) * 12 / (30 * 12 * 60), 0)                   AS utilization_pct,   -- 1 аналитик × 12 ч
       ROUND(100.0 * COUNT(*) FILTER (WHERE f.is_fraud = 0) / COUNT(*), 1) AS false_positive_pct,
       PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY done_min - created_min) AS median_minutes_to_decision,
       ROUND(PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY done_min - created_min)::numeric / 60, 1) AS p90_hours_to_decision,
       COUNT(c.alert_id)                                                  AS fraud_transfers,
       COUNT(c.alert_id) FILTER (WHERE f.done_min < c.cashout_min)        AS stopped_before_cashout,
       ROUND(SUM(f.amount) FILTER (WHERE c.alert_id IS NOT NULL AND f.done_min >= c.cashout_min) / 1e6, 2) AS fraud_lost_mln
FROM finished f
LEFT JOIN cashout c ON c.alert_id = f.alert_id;
