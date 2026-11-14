-- Шаг 0. Применяем каталог правил к операциям, считаем балл, маршрутизируем алерты и моделируем итог разбора.
-- Запуск после data/ddl.sql и data/load.sql. Работает и на настоящем PaySim (колонки те же).
-- Параметры модели вынесены в CTE params: время разбора аналитиком, аналитиков в смене.
TRUNCATE alert_decisions, alert_rule_hits, alerts, alert_rules RESTART IDENTITY;

INSERT INTO alert_rules VALUES
 ('R1', 'Обнуление кошелька переводом', 'TRANSFER на 95 %+ баланса при балансе от 10 000 ₽: типичный захват аккаунта', 50, 'Антифрод'),
 ('R2', 'Крупная сумма',                'TRANSFER или CASH_OUT больше 200 000 ₽',                                  20, 'Антифрод'),
 ('R3', 'Перевод и сразу вывод',        'CASH_OUT той же суммы (±1 %) в течение 2 часов после входящего TRANSFER: счёт дропа', 50, 'Антифрод'),
 ('R4', 'Ночная операция',              'TRANSFER или CASH_OUT от 20 000 ₽ с 00:00 до 05:59',                      15, 'Антифрод'),
 ('R5', 'Новый получатель без истории', 'TRANSFER на счёт, у которого нулевой баланс до и после операции',        30, 'Антифрод'),
 ('R6', 'Серия переводов',              '3-й и следующие TRANSFER одного клиента за 24 часа',                      20, 'Антифрод');

-- 1. Срабатывания правил: каждое правило — отдельный SELECT, всё склеиваем через UNION ALL
CREATE TEMP TABLE hits AS
SELECT tx_id, 'R1' AS rule_code FROM transactions
 WHERE type = 'TRANSFER' AND oldbalance_org >= 10000 AND amount >= 0.95 * oldbalance_org
UNION ALL
SELECT tx_id, 'R2' FROM transactions
 WHERE type IN ('TRANSFER', 'CASH_OUT') AND amount > 200000
UNION ALL
SELECT c.tx_id, 'R3' FROM transactions c
 WHERE c.type = 'CASH_OUT'
   AND EXISTS (SELECT 1 FROM transactions t
                WHERE t.type = 'TRANSFER' AND t.name_dest = c.name_orig
                  AND c.step - t.step BETWEEN 0 AND 2
                  AND ABS(c.amount - t.amount) <= 0.01 * t.amount)
UNION ALL
SELECT tx_id, 'R4' FROM transactions
 WHERE type IN ('TRANSFER', 'CASH_OUT') AND amount >= 20000 AND (step - 1) % 24 < 6
UNION ALL
SELECT tx_id, 'R5' FROM transactions
 WHERE type = 'TRANSFER' AND oldbalance_dest = 0 AND newbalance_dest = 0
UNION ALL
SELECT tx_id, 'R6' FROM (
    SELECT tx_id, COUNT(*) OVER (PARTITION BY name_orig ORDER BY step
                                 RANGE BETWEEN 23 PRECEDING AND CURRENT ROW) AS n_24h
    FROM transactions WHERE type = 'TRANSFER') s
 WHERE n_24h >= 3;

-- 2. Алерт = операция, где сработало хотя бы одно правило. Балл = сумма весов, но не больше 100.
--    Маршрут TO-BE (см. docs/rules_catalog.md, таблица триажа):
--    R3 → автоблок (SMS бессмысленна: владелец счёта дропа и есть мошенник);
--    балл ≥ 80 → автоблок; 40–79 → подтверждение клиентом; < 40 и сумма < 50 000 → только мониторинг; иначе аналитик.
INSERT INTO alerts (tx_id, created_step, score, route_to_be)
SELECT t.tx_id, t.step, LEAST(SUM(r.weight), 100) AS score,
       CASE
           WHEN BOOL_OR(h.rule_code = 'R3')        THEN 'auto_block'
           WHEN LEAST(SUM(r.weight), 100) >= 80    THEN 'auto_block'
           WHEN LEAST(SUM(r.weight), 100) >= 40    THEN 'sms_confirm'
           WHEN t.amount < 50000                   THEN 'monitor'
           ELSE                                         'analyst'
       END
FROM hits h
JOIN alert_rules r ON r.rule_code = h.rule_code
JOIN transactions t ON t.tx_id = h.tx_id
GROUP BY t.tx_id, t.step, t.amount;

INSERT INTO alert_rule_hits
SELECT DISTINCT a.alert_id, h.rule_code FROM hits h JOIN alerts a ON a.tx_id = h.tx_id;

-- 3. Модель итога разбора TO-BE. «Случайность» детерминированная: hashtext(tx_id) даёт одно и то же число
--    при каждом запуске. Допущения: клиент подтверждает свою операцию в 95 % случаев, отклоняет чужую в 85 %;
--    без ответа 15 минут — алерт уходит аналитику; разбор аналитиком 12 минут.
INSERT INTO alert_decisions
SELECT a.alert_id,
       CASE
           WHEN a.route_to_be = 'auto_block' THEN 'system'
           WHEN a.route_to_be = 'monitor'    THEN 'none'
           WHEN a.route_to_be = 'sms_confirm'
                AND rnd < CASE WHEN t.is_fraud = 1 THEN 85 ELSE 95 END THEN 'client'
           ELSE 'analyst'
       END,
       CASE
           WHEN a.route_to_be = 'monitor'    THEN 'monitored'
           WHEN a.route_to_be = 'auto_block' THEN 'blocked'
           WHEN t.is_fraud = 1               THEN 'blocked'      -- клиент или аналитик распознали мошенничество
           ELSE 'released'
       END,
       CASE
           WHEN a.route_to_be IN ('auto_block', 'monitor') THEN 0
           WHEN a.route_to_be = 'sms_confirm'
                AND rnd < CASE WHEN t.is_fraud = 1 THEN 85 ELSE 95 END THEN 1 + rnd % 9
           WHEN a.route_to_be = 'sms_confirm' THEN 15 + 12       -- ждали клиента, потом аналитик
           ELSE 12
       END,
       t.is_fraud = 1
FROM alerts a
JOIN transactions t ON t.tx_id = a.tx_id
CROSS JOIN LATERAL (SELECT ABS(hashtext(t.tx_id::text)) % 100 AS rnd) z;

SELECT route_to_be, COUNT(*) AS alerts, SUM(CASE WHEN d.is_true_positive THEN 1 ELSE 0 END) AS true_fraud
FROM alerts a JOIN alert_decisions d USING (alert_id)
GROUP BY ROLLUP (route_to_be) ORDER BY route_to_be NULLS LAST;
