-- Бизнес-вопрос (TO-BE): что даёт триаж (автоблок / подтверждение клиентом / аналитик / мониторинг)?
-- По каждому маршруту: объём, точность, кто решил, минуты работы аналитика, время до решения.
-- Работа аналитика: 12 минут на алерт маршрута analyst и на SMS-алерты, где клиент не ответил.
SELECT a.route_to_be,
       COUNT(*)                                                                AS alerts,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)                      AS share_pct,
       COUNT(*) FILTER (WHERE d.is_true_positive)                              AS true_fraud,
       ROUND(100.0 * COUNT(*) FILTER (WHERE d.is_true_positive) / COUNT(*), 1) AS precision_pct,
       COUNT(*) FILTER (WHERE d.decided_by = 'analyst')                        AS went_to_analyst,
       SUM(CASE WHEN d.decided_by = 'analyst' THEN 12 ELSE 0 END)              AS analyst_minutes,
       ROUND(AVG(d.minutes_to_decision), 1)                                    AS avg_minutes_to_decision,
       COUNT(*) FILTER (WHERE d.decision = 'blocked' AND NOT d.is_true_positive) AS legit_blocked
FROM alerts a
JOIN alert_decisions d USING (alert_id)
GROUP BY a.route_to_be
ORDER BY a.route_to_be;

-- Итог: нагрузка на аналитиков было / стало
SELECT ROUND(COUNT(*) * 12 / 60.0 / 30, 1)                                                AS as_is_analyst_hours_per_day,
       ROUND(COUNT(*) FILTER (WHERE d.decided_by = 'analyst') * 12 / 60.0 / 30, 1)       AS to_be_analyst_hours_per_day,
       ROUND(100 - 100.0 * COUNT(*) FILTER (WHERE d.decided_by = 'analyst') / COUNT(*), 0) AS workload_cut_pct
FROM alerts a JOIN alert_decisions d USING (alert_id);
