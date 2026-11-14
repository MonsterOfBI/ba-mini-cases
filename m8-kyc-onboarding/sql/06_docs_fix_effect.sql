-- 6. Оценка эффекта: что даст починка шага «Документы» на телефоне.
-- Допущение: после изменений (сжатие фото в приложении, съёмка камерой с рамкой, не просить «свидетельство ОГРНИП» —
-- банк сам берёт выписку ЕГРИП) с телефона бросают не чаще, чем сейчас с компьютера. Это оценка, а не факт:
-- проверять A/B-тестом (docs/kpi.md, KPI-2).
WITH per_app AS (
    SELECT a.app_id, a.device,
           bool_or(e.step = 'form_submitted')                       AS reached_docs,
           bool_or(e.step = 'abandoned' AND e.detail = 'documents') AS dropped_docs,
           bool_or(e.step = 'docs_uploaded')                        AS uploaded,
           bool_or(e.step = 'account_opened')                       AS opened
    FROM applications a
    JOIN app_events e USING (app_id)
    GROUP BY a.app_id, a.device
),
rates AS (
    SELECT COUNT(*) FILTER (WHERE reached_docs AND device = 'mobile')                                  AS mobile_reached,
           1.0 * COUNT(*) FILTER (WHERE dropped_docs AND device = 'mobile')
               / COUNT(*) FILTER (WHERE reached_docs AND device = 'mobile')                            AS mobile_drop,
           1.0 * COUNT(*) FILTER (WHERE dropped_docs AND device = 'desktop')
               / COUNT(*) FILTER (WHERE reached_docs AND device = 'desktop')                           AS target_drop,
           1.0 * COUNT(*) FILTER (WHERE opened) / COUNT(*) FILTER (WHERE uploaded)                     AS after_docs_conv,
           COUNT(*) FILTER (WHERE opened)                                                              AS opened_now
    FROM per_app
)
SELECT mobile_reached,
       ROUND(100 * mobile_drop, 1)                                               AS mobile_drop_now_pct,
       ROUND(100 * target_drop, 1)                                               AS mobile_drop_target_pct,
       ROUND(mobile_reached * (mobile_drop - target_drop))                       AS extra_uploads,
       ROUND(100 * after_docs_conv, 1)                                           AS after_docs_conv_pct,
       ROUND(mobile_reached * (mobile_drop - target_drop) * after_docs_conv)     AS extra_accounts_3m,
       opened_now,
       ROUND(100 * mobile_reached * (mobile_drop - target_drop) * after_docs_conv / opened_now, 1) AS growth_pct
FROM rates;
