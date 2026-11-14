-- Бизнес-вопрос: сколько честных клиентов мы беспокоим? Антифрод, который блокирует всех, тоже плохой.
-- Считаем на 1 000 операций: SMS-запросы честным клиентам, ошибочные блокировки (клиент звонит в поддержку).
WITH base AS (SELECT COUNT(*) AS tx FROM transactions)
SELECT COUNT(*) FILTER (WHERE a.route_to_be = 'sms_confirm' AND NOT d.is_true_positive)                     AS legit_sms,
       COUNT(*) FILTER (WHERE d.decision = 'blocked' AND NOT d.is_true_positive)                            AS legit_blocked,
       ROUND(1000.0 * COUNT(*) FILTER (WHERE a.route_to_be = 'sms_confirm' AND NOT d.is_true_positive) / b.tx, 2) AS legit_sms_per_1000_tx,
       ROUND(1000.0 * COUNT(*) FILTER (WHERE d.decision = 'blocked' AND NOT d.is_true_positive) / b.tx, 2)  AS legit_blocked_per_1000_tx,
       ROUND(100.0 * COUNT(*) FILTER (WHERE d.decision = 'blocked' AND d.is_true_positive)
             / NULLIF(COUNT(*) FILTER (WHERE d.decision = 'blocked'), 0), 1)                                AS block_precision_pct
FROM alerts a
JOIN alert_decisions d USING (alert_id)
CROSS JOIN base b
GROUP BY b.tx;
