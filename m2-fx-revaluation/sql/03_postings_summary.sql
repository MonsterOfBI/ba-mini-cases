-- Бизнес-вопрос: какие проводки сделать за месяц и какой итог курсовых разниц в 91 счёте?
-- Положительная разница → Кт 91.01 (прочие доходы), отрицательная → Дт 91.02 (прочие расходы).
WITH r AS (SELECT * FROM v_revaluation)
SELECT date_trunc('month', event_date)::date              AS месяц,
       account                                            AS счёт,
       CASE WHEN fx_result >= 0 THEN 'Дт ' || account || ' Кт 91.01' ELSE 'Дт 91.02 Кт ' || account END AS проводка,
       count(*)                                           AS строк,
       sum(abs(fx_result))                                AS сумма_руб
FROM r
WHERE fx_result <> 0
GROUP BY 1, 2, 3
ORDER BY 1, 2, 3;

-- Итог по месяцам: сколько курсовые разницы добавили к прибыли (+) или отняли (−)
SELECT date_trunc('month', event_date)::date AS месяц,
       sum(fx_result) FILTER (WHERE event_type = 'переоценка') AS переоценка_на_конец_месяца,
       sum(fx_result) FILTER (WHERE event_type = 'погашение')  AS при_погашении,
       sum(fx_result)                                          AS итого
FROM v_revaluation
GROUP BY 1
ORDER BY 1;
