-- Бизнес-вопрос: кого и до какого числа уведомить о новой ставке на следующий процентный период?
-- BR-06: уведомляем клиента, если ставка меняется, не позже чем за min_notice_days до начала периода.
-- Дата фиксации = начало периода − 10 дней, значит на уведомление есть 3 дня: (10 − 7).
-- Пример — период август 2026: КС на фиксацию 14,25 % вместо 14,50 %.
\set period '''2026-08-01'''
WITH cur AS (SELECT * FROM v_loan_interest WHERE period_start = :period),
     prev AS (SELECT loan_id, applied_rate FROM v_loan_interest WHERE period_start = (:period::date - interval '1 month')::date)
SELECT c.contract_no AS договор, c.client AS клиент, c.notify_channel AS канал,
       p.applied_rate AS была, c.applied_rate AS будет, c.applied_rate - p.applied_rate AS изменение,
       CASE WHEN c.at_floor THEN 'пол' WHEN c.at_cap THEN 'потолок' ELSE '' END AS ограничение,
       (c.period_start - rp.min_notice_days) AS уведомить_до
FROM cur c JOIN prev p USING (loan_id) CROSS JOIN rate_params rp
WHERE c.applied_rate <> p.applied_rate
ORDER BY изменение, договор;

-- Сводка: сколько клиентов уведомить, а у скольких ставка не изменилась из-за пола
WITH cur AS (SELECT * FROM v_loan_interest WHERE period_start = :period),
     prev AS (SELECT loan_id, applied_rate FROM v_loan_interest WHERE period_start = (:period::date - interval '1 month')::date)
SELECT count(*) FILTER (WHERE c.applied_rate <> p.applied_rate)                AS уведомить,
       count(*) FILTER (WHERE c.applied_rate = p.applied_rate AND c.at_floor)  AS не_меняется_пол,
       count(*) FILTER (WHERE c.applied_rate = p.applied_rate AND NOT c.at_floor) AS не_меняется_прочие
FROM cur c JOIN prev p USING (loan_id);
