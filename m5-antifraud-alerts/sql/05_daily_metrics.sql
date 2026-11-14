-- Бизнес-вопрос: как процесс выглядит день за днём? Это источник данных для дашборда (DataLens).
-- Одна строка = день × маршрут. Выгрузка в CSV:  \copy (...) TO 'dashboard/daily_metrics.csv' CSV HEADER
SELECT (DATE '2026-09-01' + (a.created_step - 1) / 24)                 AS day,
       a.route_to_be                                                   AS route,
       COUNT(*)                                                        AS alerts,
       COUNT(*) FILTER (WHERE d.is_true_positive)                      AS confirmed_fraud,
       COUNT(*) FILTER (WHERE NOT d.is_true_positive)                  AS false_positives,
       COUNT(*) FILTER (WHERE d.decided_by = 'analyst')                AS analyst_alerts,
       ROUND(AVG(d.minutes_to_decision), 1)                            AS avg_minutes_to_decision
FROM alerts a
JOIN alert_decisions d USING (alert_id)
GROUP BY 1, 2
ORDER BY 1, 2;
