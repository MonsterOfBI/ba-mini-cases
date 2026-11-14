-- 1. Воронка онбординга: сколько заявок дошло до каждого шага и где теряем больше всего.
-- Бизнес-вопрос: «Где клиенты бросают заявку?»
-- «Одобрена» = маршрут auto или итоговое решение комплаенса approved.
WITH reached AS (
    SELECT a.app_id,
           TRUE                                                                     AS started,
           bool_or(e.step = 'form_submitted')                                       AS form_submitted,
           bool_or(e.step = 'docs_uploaded')                                        AS docs_uploaded,
           bool_or(e.step = 'checks_done')                                          AS checks_done,
           bool_or(e.step = 'checks_done' AND e.detail = 'auto')
               OR bool_or(e.step = 'review_done' AND e.detail = 'approved')         AS approved,
           bool_or(e.step = 'identified')                                           AS identified,
           bool_or(e.step = 'account_opened')                                       AS account_opened
    FROM applications a
    JOIN app_events e USING (app_id)
    GROUP BY a.app_id
),
funnel AS (
    SELECT 1 AS n, 'Начал заявку' AS step, COUNT(*) FILTER (WHERE started) AS apps FROM reached
    UNION ALL SELECT 2, 'Заполнил анкету',       COUNT(*) FILTER (WHERE form_submitted) FROM reached
    UNION ALL SELECT 3, 'Загрузил документы',    COUNT(*) FILTER (WHERE docs_uploaded)  FROM reached
    UNION ALL SELECT 4, 'Прошёл автопроверки',   COUNT(*) FILTER (WHERE checks_done)    FROM reached
    UNION ALL SELECT 5, 'Одобрен',               COUNT(*) FILTER (WHERE approved)       FROM reached
    UNION ALL SELECT 6, 'Идентифицирован',       COUNT(*) FILTER (WHERE identified)     FROM reached
    UNION ALL SELECT 7, 'Счёт открыт',           COUNT(*) FILTER (WHERE account_opened) FROM reached
)
SELECT n, step, apps,
       LAG(apps) OVER (ORDER BY n) - apps                                         AS lost,
       ROUND(100.0 * apps / LAG(apps) OVER (ORDER BY n), 1)                       AS conv_from_prev_pct,
       ROUND(100.0 * apps / FIRST_VALUE(apps) OVER (ORDER BY n), 1)               AS conv_from_start_pct
FROM funnel
ORDER BY n;

-- Где бросили (по шагу, на котором заявка закрылась по таймауту 14 дней)
SELECT e.detail AS abandoned_at, COUNT(*) AS apps,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS share_of_abandoned_pct
FROM app_events e
WHERE e.step = 'abandoned'
GROUP BY e.detail
ORDER BY apps DESC;
