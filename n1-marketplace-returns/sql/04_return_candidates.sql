-- Бизнес-вопрос: сколько заказов — вероятные возвраты/претензии и на какую сумму?
-- В Olist нет таблицы возвратов, поэтому используем прокси (допущение, см. README):
--   оценка 1–2 И (опоздание ИЛИ комментарий о дефекте/неполучении/не тот товар).
WITH flags AS (
    SELECT o.order_id,
           SUM(oi.price)                                                      AS order_value,
           MAX(r.review_score)                                                AS score,
           BOOL_OR(o.order_delivered_customer_date > o.order_estimated_delivery_date) AS late,
           BOOL_OR(r.review_comment_message ~* 'defeito|errado|não recebi')   AS complaint
    FROM orders o
    JOIN order_items oi  ON oi.order_id = o.order_id
    JOIN order_reviews r ON r.order_id = o.order_id
    WHERE o.order_status = 'delivered'
    GROUP BY o.order_id
)
SELECT COUNT(*) FILTER (WHERE score <= 2 AND (late OR complaint))                        AS return_candidates,
       ROUND(100.0 * COUNT(*) FILTER (WHERE score <= 2 AND (late OR complaint)) / COUNT(*), 1) AS share_pct,
       SUM(order_value) FILTER (WHERE score <= 2 AND (late OR complaint))               AS value_at_risk,
       COUNT(*) FILTER (WHERE score <= 2 AND complaint AND NOT late)                     AS quality_not_logistics
FROM flags;
