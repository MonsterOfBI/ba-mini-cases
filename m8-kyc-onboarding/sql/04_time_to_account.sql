-- 4. Сколько ждёт клиент: от начала заявки до открытого счёта и ожидание в очереди комплаенса.
-- Бизнес-вопрос: «Почему счёт открывается два-три дня, а не за час?»

-- 4.1. Время до счёта по маршруту и способу идентификации, часы
WITH t AS (
    SELECT a.app_id, a.route_as_is,
           MAX(e.detail) FILTER (WHERE e.step = 'identified')                         AS id_method,
           EXTRACT(EPOCH FROM MAX(e.event_at) FILTER (WHERE e.step = 'account_opened')
                             - MIN(e.event_at) FILTER (WHERE e.step = 'started')) / 3600 AS hours
    FROM applications a
    JOIN app_events e USING (app_id)
    WHERE a.final_status = 'opened'
    GROUP BY a.app_id, a.route_as_is
)
SELECT COALESCE(route_as_is, 'все') AS route, COALESCE(id_method, 'все') AS id_method,
       COUNT(*) AS accounts,
       ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY hours)::numeric, 1) AS median_h,
       ROUND(PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY hours)::numeric, 1) AS p90_h
FROM t
GROUP BY GROUPING SETS ((route_as_is, id_method), ())
ORDER BY route_as_is NULLS LAST, id_method;

-- 4.2. Ожидание в очереди комплаенса (автопроверки → взяли в работу), календарные часы, и доля в SLA 4 часа
WITH q AS (
    SELECT c.app_id, EXTRACT(EPOCH FROM s.event_at - c.event_at) / 3600 AS wait_h
    FROM app_events c
    JOIN app_events s ON s.app_id = c.app_id AND s.step = 'review_started'
    WHERE c.step = 'checks_done'
)
SELECT COUNT(*) AS reviews,
       ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY wait_h)::numeric, 1) AS median_wait_h,
       ROUND(PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY wait_h)::numeric, 1) AS p90_wait_h,
       ROUND(100.0 * COUNT(*) FILTER (WHERE wait_h <= 4) / COUNT(*), 1)       AS within_4h_pct
FROM q;
