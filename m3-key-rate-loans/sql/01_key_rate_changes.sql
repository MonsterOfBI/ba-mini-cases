-- Бизнес-вопрос: когда менялась ключевая ставка и какая ставка попала в каждую дату фиксации?
-- 1) Даты изменений: сравниваем ставку дня с предыдущим днём (LAG)
WITH d AS (
    SELECT rate_date, key_rate, LAG(key_rate) OVER (ORDER BY rate_date) AS prev_rate
    FROM key_rate
)
SELECT rate_date AS действует_с, prev_rate AS было, key_rate AS стало, key_rate - prev_rate AS изменение_пп
FROM d
WHERE prev_rate IS NOT NULL AND key_rate <> prev_rate
ORDER BY rate_date;

-- 2) Дата фиксации = 1-е число месяца минус lookback (BR-03). Берём ставку, действующую на эту дату.
SELECT m::date                                   AS процентный_период,
       (m - make_interval(days => p.lookback_days))::date AS дата_фиксации,
       kr.key_rate                               AS ключевая_на_фиксацию
FROM generate_series(date '2025-01-01', date '2026-12-01', interval '1 month') m
CROSS JOIN rate_params p
CROSS JOIN LATERAL (
    SELECT key_rate FROM key_rate
    WHERE rate_date <= (m - make_interval(days => p.lookback_days))::date
    ORDER BY rate_date DESC LIMIT 1
) kr
ORDER BY 1;
