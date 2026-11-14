-- Бизнес-вопрос: как решения ЦБ повлияли на процентный доход банка и что дали пол и потолок?
SELECT period_start                                                   AS месяц,
       max(key_rate)                                                  AS кс,
       count(*)                                                       AS кредитов,
       round(sum(balance * applied_rate) / sum(balance), 2)           AS средневзв_ставка,
       round(sum(interest) / 1e6, 2)                                  AS доход_млн,
       round(sum(interest - interest_no_limits) FILTER (WHERE at_floor) / 1e6, 2) AS эффект_пола_млн,   -- банк получил больше
       round(sum(interest - interest_no_limits) FILTER (WHERE at_cap)   / 1e6, 2) AS эффект_потолка_млн, -- банк недополучил
       count(*) FILTER (WHERE at_floor)                               AS на_полу,
       count(*) FILTER (WHERE at_cap)                                 AS на_потолке
FROM v_loan_interest
WHERE period_start <= date '2026-12-01'
GROUP BY period_start
ORDER BY period_start;

-- Итог по годам
SELECT extract(year FROM period_start)::int AS год,
       round(sum(interest) / 1e6, 1)                                         AS доход_млн,
       round(sum(interest - interest_no_limits) FILTER (WHERE at_floor) / 1e6, 1) AS пол_добавил_млн,
       round(sum(interest - interest_no_limits) FILTER (WHERE at_cap) / 1e6, 1)   AS потолок_отнял_млн
FROM v_loan_interest
GROUP BY 1 ORDER BY 1;
