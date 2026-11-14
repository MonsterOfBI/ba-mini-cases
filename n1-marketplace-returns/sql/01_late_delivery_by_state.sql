-- Бизнес-вопрос: в каких регионах товар чаще приезжает позже обещанного срока?
-- Опоздание — главный повод для претензии и возврата.
SELECT c.customer_state                                                         AS state,
       COUNT(*)                                                                 AS delivered,
       ROUND(100.0 * AVG((o.order_delivered_customer_date > o.order_estimated_delivery_date)::int), 1) AS late_pct,
       ROUND(AVG(EXTRACT(EPOCH FROM o.order_delivered_customer_date - o.order_purchase_timestamp) / 86400)::numeric, 1) AS avg_days_to_deliver
FROM orders o
JOIN customers c ON c.customer_id = o.customer_id
WHERE o.order_status = 'delivered'
  AND o.order_delivered_customer_date IS NOT NULL      -- в настоящем Olist есть delivered без даты
GROUP BY c.customer_state
ORDER BY late_pct DESC;
