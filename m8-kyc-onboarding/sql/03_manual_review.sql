-- 3. Ручная проверка комплаенса: сколько, почему, чем заканчивается.
-- Бизнес-вопрос: «Как снизить долю ручных проверок без роста риска?» — сначала понять, какие проверки ничего не меняют.

-- 3.1. Маршрут после автопроверок (AS-IS)
SELECT route_as_is, COUNT(*) AS apps,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS share_pct
FROM applications
WHERE route_as_is IS NOT NULL
GROUP BY route_as_is
ORDER BY apps DESC;

-- 3.2. Почему заявка ушла на ручную проверку. Причины пересекаются, поэтому берём первую по порядку правила AS-IS.
SELECT CASE
           WHEN form_mismatch AND NOT real_mismatch THEN '1. Анкета не совпала (опечатка, ё/е, формат адреса)'
           WHEN real_mismatch                     THEN '2. Настоящее расхождение с паспортом/ЕГРИП'
           WHEN zsk_group = 'medium'              THEN '3. ЗСК: жёлтая группа'
           WHEN zsk_group = 'none'                THEN '4. ЗСК: группы ещё нет (новый ИП)'
           WHEN okved_watch                       THEN '5. ОКВЭД из списка внимания'
       END AS first_reason,
       COUNT(*) AS apps,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS share_pct
FROM applications
WHERE route_as_is = 'manual'
GROUP BY 1
ORDER BY 1;

-- 3.3. Итог первой ручной проверки по группе ЗСК: у «зелёной» группы отказов нет и быть не может
--      (банк не вправе отказать клиенту с низким риском по основаниям 115-ФЗ), проверка только задерживает.
WITH first_review AS (
    SELECT DISTINCT ON (app_id) app_id, detail AS outcome
    FROM app_events
    WHERE step = 'review_done'
    ORDER BY app_id, event_at
)
SELECT a.zsk_group,
       COUNT(*)                                                         AS reviewed,
       COUNT(*) FILTER (WHERE r.outcome = 'approved')                   AS approved,
       COUNT(*) FILTER (WHERE r.outcome = 'info_requested')             AS info_requested,
       COUNT(*) FILTER (WHERE r.outcome = 'refused')                    AS refused,
       COUNT(*) FILTER (WHERE a.is_risky)                               AS risky_truth,
       ROUND(100.0 * COUNT(*) FILTER (WHERE r.outcome = 'refused') / COUNT(*), 1) AS refuse_pct
FROM first_review r
JOIN applications a USING (app_id)
GROUP BY ROLLUP (a.zsk_group)
ORDER BY a.zsk_group NULLS LAST;

-- 3.4. Запрос пояснений: сколько из них — из-за «ложного» расхождения и сколько клиентов после этого ушло
SELECT a.real_mismatch,
       COUNT(*)                                                           AS info_requests,
       COUNT(*) FILTER (WHERE a.final_status = 'abandoned')               AS abandoned_after,
       ROUND(100.0 * COUNT(*) FILTER (WHERE a.final_status = 'abandoned') / COUNT(*), 1) AS abandoned_pct
FROM app_events e
JOIN applications a USING (app_id)
WHERE e.step = 'review_done' AND e.detail = 'info_requested'
GROUP BY a.real_mismatch;

-- 3.5. Нагрузка на комплаенс: минуты проверки (от взятия в работу до решения) за 3 месяца
SELECT COUNT(*)                                                     AS reviews,
       ROUND(SUM(EXTRACT(EPOCH FROM d.event_at - s.event_at)) / 3600, 0) AS review_hours_total,
       ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM d.event_at - s.event_at) / 60)::numeric, 1) AS median_min
FROM app_events s
JOIN LATERAL (SELECT event_at FROM app_events d
              WHERE d.app_id = s.app_id AND d.step = 'review_done' AND d.event_at > s.event_at
              ORDER BY d.event_at LIMIT 1) d ON TRUE
WHERE s.step = 'review_started';
