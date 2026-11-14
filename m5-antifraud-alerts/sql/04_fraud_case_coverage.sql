-- Бизнес-вопрос: сколько мошеннических схем (перевод жертвы → вывод дропом) TO-BE останавливает и где?
-- Схема = TRANSFER жертвы на счёт дропа + один или несколько CASH_OUT с этого счёта (иногда выводят частями).
-- Спасённая сумма: весь перевод, если заблокирован TRANSFER; иначе — сумма заблокированных выводов.
-- Временное представление (TEMP VIEW) нужно, чтобы два итоговых запроса ниже использовали одну логику.
CREATE OR REPLACE TEMP VIEW fraud_case_status AS
WITH cases AS (
    SELECT tr.tx_id AS transfer_id, tr.name_dest AS mule, tr.amount, at.route_to_be AS transfer_route,
           COALESCE(dt.decision = 'blocked', FALSE) AS blocked_at_transfer
    FROM transactions tr
    LEFT JOIN alerts at          ON at.tx_id = tr.tx_id
    LEFT JOIN alert_decisions dt ON dt.alert_id = at.alert_id
    WHERE tr.type = 'TRANSFER' AND tr.is_fraud = 1
),
cashouts AS (                                -- выводы дропа и их судьба
    SELECT co.name_orig AS mule,
           COUNT(*)                                                          AS n_cashouts,
           SUM(co.amount) FILTER (WHERE dc.decision = 'blocked')             AS blocked_amount
    FROM transactions co
    LEFT JOIN alerts ac          ON ac.tx_id = co.tx_id
    LEFT JOIN alert_decisions dc ON dc.alert_id = ac.alert_id
    WHERE co.type = 'CASH_OUT' AND co.is_fraud = 1
    GROUP BY co.name_orig
),
status AS (
    SELECT c.*, co.n_cashouts,
           CASE WHEN c.blocked_at_transfer THEN c.amount ELSE COALESCE(co.blocked_amount, 0) END AS saved
    FROM cases c LEFT JOIN cashouts co ON co.mule = c.mule
)
SELECT * FROM status;

SELECT COUNT(*)                                                               AS fraud_cases,
       COUNT(*) FILTER (WHERE n_cashouts > 1)                                 AS split_cashouts,
       COUNT(*) FILTER (WHERE blocked_at_transfer)                            AS stopped_at_transfer,
       COUNT(*) FILTER (WHERE NOT blocked_at_transfer AND saved >= amount)    AS stopped_at_cashout,
       COUNT(*) FILTER (WHERE NOT blocked_at_transfer AND saved > 0 AND saved < amount) AS partly_saved,
       COUNT(*) FILTER (WHERE saved = 0)                                      AS missed,
       ROUND(SUM(amount) / 1e6, 2)                                            AS fraud_amount_mln,
       ROUND(SUM(saved) / 1e6, 2)                                             AS saved_mln,
       ROUND(100.0 * SUM(saved) / SUM(amount), 1)                             AS saved_pct
FROM fraud_case_status;

-- Пропущенные схемы: по каким маршрутам прошёл перевод — материал для улучшения правил
SELECT COALESCE(transfer_route, 'без алерта') AS transfer_route, COUNT(*) AS missed_cases, ROUND(SUM(amount)) AS missed_amount
FROM fraud_case_status WHERE saved = 0
GROUP BY 1 ORDER BY 2 DESC;
