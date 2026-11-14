-- Бизнес-вопрос: правда ли, что опоздание приводит к низкой оценке (кандидаты на возврат и жалобу)?
SELECT CASE WHEN o.order_delivered_customer_date > o.order_estimated_delivery_date
            THEN 'опоздал' ELSE 'вовремя' END                   AS delivery,
       COUNT(*)                                                 AS orders,
       ROUND(AVG(r.review_score), 2)                            AS avg_score,
       ROUND(100.0 * AVG((r.review_score <= 2)::int), 1)        AS low_score_pct
FROM orders o
JOIN order_reviews r ON r.order_id = o.order_id
WHERE o.order_status = 'delivered' AND o.order_delivered_customer_date IS NOT NULL
GROUP BY 1;
