-- Бизнес-вопрос: какие правила полезны, а какие только «шумят»?
-- Для каждого правила: сколько алертов дало, сколько из них настоящее мошенничество (precision — точность),
-- какую долю всех мошеннических операций поймало (recall — полнота) и сколько мошенничества поймало ТОЛЬКО оно.
-- Precision = подтверждённые / все алерты правила. Recall = пойманные правилом мошеннические / все мошеннические.
WITH fraud_total AS (
    SELECT COUNT(*) AS n FROM transactions WHERE is_fraud = 1
),
per_alert AS (
    SELECT a.alert_id, t.is_fraud, COUNT(*) OVER (PARTITION BY a.alert_id) AS rules_in_alert, h.rule_code
    FROM alerts a
    JOIN alert_rule_hits h USING (alert_id)
    JOIN transactions t USING (tx_id)
)
SELECT r.rule_code, r.name, r.weight,
       COUNT(p.alert_id)                                                        AS alerts,
       COUNT(p.alert_id) FILTER (WHERE p.is_fraud = 1)                          AS fraud_hits,
       ROUND(100.0 * COUNT(p.alert_id) FILTER (WHERE p.is_fraud = 1) / NULLIF(COUNT(p.alert_id), 0), 1) AS precision_pct,
       ROUND(100.0 * COUNT(p.alert_id) FILTER (WHERE p.is_fraud = 1) / (SELECT n FROM fraud_total), 1)   AS recall_pct,
       COUNT(p.alert_id) FILTER (WHERE p.is_fraud = 1 AND p.rules_in_alert = 1) AS fraud_only_this_rule
FROM alert_rules r
LEFT JOIN per_alert p ON p.rule_code = r.rule_code
GROUP BY r.rule_code, r.name, r.weight
ORDER BY r.rule_code;
