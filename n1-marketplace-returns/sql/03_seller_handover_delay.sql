-- Бизнес-вопрос: кто виноват в опоздании — продавец (поздно передал в доставку) или логистика?
-- Продавец нарушил срок, если order_delivered_carrier_date > shipping_limit_date.
WITH per_seller AS (
    SELECT oi.seller_id,
           COUNT(*)                                                                   AS items,
           AVG((o.order_delivered_carrier_date > oi.shipping_limit_date)::int)        AS late_handover_share
    FROM order_items oi
    JOIN orders o ON o.order_id = oi.order_id
    WHERE o.order_delivered_carrier_date IS NOT NULL
    GROUP BY oi.seller_id
    HAVING COUNT(*) >= 30                      -- мелких продавцов не оцениваем: мало данных
)
SELECT LEFT(seller_id, 8)                        AS seller,
       items,
       ROUND(100 * late_handover_share, 1)       AS late_handover_pct,
       RANK() OVER (ORDER BY late_handover_share DESC) AS rnk
FROM per_seller
ORDER BY rnk
LIMIT 10;
