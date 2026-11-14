-- 5. KPI онбординга по месяцам — строки для дашборда (определения KPI — docs/kpi.md).
WITH per_app AS (
    SELECT a.app_id, date_trunc('month', a.created_at)::date AS month, a.device, a.route_as_is, a.final_status,
           bool_or(e.step = 'form_submitted')                          AS reached_docs,
           bool_or(e.step = 'abandoned' AND e.detail = 'documents')    AS dropped_docs,
           EXTRACT(EPOCH FROM MAX(e.event_at) FILTER (WHERE e.step = 'account_opened')
                             - MIN(e.event_at) FILTER (WHERE e.step = 'started')) / 3600 AS hours_to_account
    FROM applications a
    JOIN app_events e USING (app_id)
    GROUP BY a.app_id, month, a.device, a.route_as_is, a.final_status
)
SELECT month,
       COUNT(*)                                                                                   AS applications,
       COUNT(*) FILTER (WHERE final_status = 'opened')                                            AS accounts_opened,
       ROUND(100.0 * COUNT(*) FILTER (WHERE final_status = 'opened') / COUNT(*), 1)               AS kpi1_conversion_pct,
       ROUND(100.0 * COUNT(*) FILTER (WHERE dropped_docs AND device = 'mobile')
                   / NULLIF(COUNT(*) FILTER (WHERE reached_docs AND device = 'mobile'), 0), 1)    AS kpi2_mobile_docs_drop_pct,
       ROUND(100.0 * COUNT(*) FILTER (WHERE route_as_is = 'manual')
                   / NULLIF(COUNT(*) FILTER (WHERE route_as_is IS NOT NULL), 0), 1)               AS kpi3_manual_share_pct,
       ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY hours_to_account)::numeric, 1)          AS kpi4_median_hours_to_account,
       COUNT(*) FILTER (WHERE final_status = 'refused')                                           AS refused
FROM per_app
GROUP BY month
ORDER BY month;
