-- Бизнес-вопрос: что будет с доходом и клиентами, если ЦБ снизит ставку до 13 % (сценарий, не прогноз)?
-- Берём портфель декабря 2026 и подставляем КС = 13 вместо фактической.
WITH base AS (SELECT * FROM v_loan_interest WHERE period_start = date '2026-12-01'),
s AS (
    SELECT b.*, 13.00 AS kr_new,
           round(LEAST(GREATEST(13.00 + margin_pp, COALESCE(floor_pct, 0)), COALESCE(cap_pct, 999)), 2) AS rate_new
    FROM base b
)
SELECT round(sum(interest) / 1e6, 2)                                            AS доход_сейчас_млн,
       round(sum(balance * rate_new / 100 * days / 365) / 1e6, 2)                 AS доход_при_13_млн,
       round(sum(balance * rate_new / 100 * days / 365 - interest) / 1e6, 2)     AS разница_млн,
       count(*) FILTER (WHERE at_floor)                                           AS на_полу_сейчас,
       count(*) FILTER (WHERE floor_pct IS NOT NULL AND 13.00 + margin_pp < floor_pct) AS на_полу_при_13
FROM s;
