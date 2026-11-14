-- 2. Шаг «Документы»: почему с телефона бросают в 2+ раза чаще.
-- Бизнес-вопрос: «Что чинить первым на шаге загрузки?»

-- 2.1. Доля брошенных на шаге документов среди дошедших до него, по устройству
WITH at_docs AS (
    SELECT a.app_id, a.device,
           bool_or(e.step = 'abandoned' AND e.detail = 'documents') AS dropped,
           COUNT(*) FILTER (WHERE e.step = 'upload_error')           AS errors
    FROM applications a
    JOIN app_events e USING (app_id)
    WHERE EXISTS (SELECT 1 FROM app_events f WHERE f.app_id = a.app_id AND f.step = 'form_submitted')
    GROUP BY a.app_id, a.device
)
SELECT device,
       COUNT(*)                                                    AS reached_docs,
       COUNT(*) FILTER (WHERE dropped)                             AS dropped,
       ROUND(100.0 * COUNT(*) FILTER (WHERE dropped) / COUNT(*), 1) AS drop_pct,
       ROUND(100.0 * COUNT(*) FILTER (WHERE errors > 0) / COUNT(*), 1) AS had_error_pct
FROM at_docs
GROUP BY ROLLUP (device)
ORDER BY device NULLS LAST;

-- 2.2. Ошибки загрузки по причинам и устройствам
SELECT a.device, e.detail AS error_reason, COUNT(*) AS errors,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY a.device), 1) AS share_in_device_pct
FROM app_events e
JOIN applications a USING (app_id)
WHERE e.step = 'upload_error'
GROUP BY a.device, e.detail
ORDER BY a.device, errors DESC;

-- 2.3. Чем больше ошибок, тем чаще бросают: вероятность бросить в зависимости от числа ошибок
WITH at_docs AS (
    SELECT a.app_id,
           COUNT(*) FILTER (WHERE e.step = 'upload_error')                      AS errors,
           bool_or(e.step = 'abandoned' AND e.detail = 'documents')             AS dropped
    FROM applications a
    JOIN app_events e USING (app_id)
    WHERE EXISTS (SELECT 1 FROM app_events f WHERE f.app_id = a.app_id AND f.step = 'form_submitted')
    GROUP BY a.app_id
)
SELECT LEAST(errors, 3) AS errors_bucket,   -- 3 = «3 и больше»
       COUNT(*) AS apps,
       ROUND(100.0 * COUNT(*) FILTER (WHERE dropped) / COUNT(*), 1) AS drop_pct
FROM at_docs
GROUP BY 1
ORDER BY 1;
