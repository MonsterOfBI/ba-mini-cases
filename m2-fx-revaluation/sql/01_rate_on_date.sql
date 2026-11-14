-- Бизнес-вопрос: какой курс применять на дату, если ЦБ в этот день курс не устанавливал?
-- Правило BR-03: берём последний курс с датой установления <= нужной даты (курс «действующий на дату»).
-- Пример: курс на воскресенье 01.11.2026 = курс, установленный на субботу 31.10.
WITH asked(d) AS (VALUES (date '2026-10-31'), (date '2026-11-01'), (date '2026-10-20'))
SELECT a.d                AS нужная_дата,
       r.char_code        AS валюта,
       r.rate_date        AS дата_курса,
       r.unit_rate        AS курс,
       a.d - r.rate_date  AS дней_разницы          -- больше 3 — повод проверить, не упала ли загрузка
FROM asked a
CROSS JOIN (SELECT DISTINCT char_code FROM fx_rates) c
CROSS JOIN LATERAL (
    SELECT * FROM fx_rates r
    WHERE r.char_code = c.char_code AND r.rate_date <= a.d
    ORDER BY r.rate_date DESC
    LIMIT 1
) r
ORDER BY a.d, r.char_code;
