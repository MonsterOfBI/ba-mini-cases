-- Бизнес-вопрос: как возвраты влияют на кэшбэк? (правило CB-07: возврат списывает кэшбэк в месяце возврата)
-- Особый случай: покупка в одном месяце, возврат — в следующем. Кэшбэк уже выплачен, списываем из нового месяца.
-- Если в новом месяце начислений меньше, чем списание, у клиента «минус» — переносим на следующий месяц (CB-08).
WITH refunds AS (
    SELECT r.tx_id, r.client_id, r.tx_date AS refund_date, pc.tx_date AS purchase_date, pc.cashback,
           date_trunc('month', r.tx_date) <> date_trunc('month', pc.tx_date) AS cross_month
    FROM transactions r
    JOIN v_purchase_cashback pc ON pc.tx_id = r.original_tx_id
    WHERE r.tx_type = 'refund'
)
SELECT COUNT(*)                                       AS refunds,
       COUNT(*) FILTER (WHERE cashback > 0)           AS refunds_with_cashback,
       ROUND(SUM(cashback))                           AS cashback_reversed,
       COUNT(*) FILTER (WHERE cross_month)            AS cross_month_refunds,
       ROUND(SUM(cashback) FILTER (WHERE cross_month)) AS reversed_from_next_month,
       (SELECT COUNT(*) FROM v_client_month WHERE net_cashback < 0) AS client_months_negative
FROM refunds;
