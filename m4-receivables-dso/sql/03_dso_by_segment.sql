-- Бизнес-вопрос: DSO выше отсрочки по договору — у кого именно? Сравниваем «реальный» срок оплаты с договорным.
-- Метрика для одной оплаченной реализации: дней от отгрузки до последнего платежа (закрытия долга).
-- Средневзвешенный по сумме срок ≈ DSO сегмента; разница с отсрочкой — «лишние дни» денег у клиента.
WITH closed AS (
    SELECT s.doc_id, s.customer_id, s.amount, s.shipped_at,
           MAX(r.paid_at) AS closed_at
    FROM sales_docs s
    JOIN receipts r ON r.doc_id = s.doc_id
    GROUP BY s.doc_id, s.customer_id, s.amount, s.shipped_at
    HAVING SUM(r.amount) >= s.amount         -- только полностью оплаченные
)
SELECT c.segment,
       COUNT(*)                                                             AS docs_closed,
       ROUND(AVG(c.payment_terms_days), 0)                                  AS avg_terms_days,
       ROUND(SUM((cl.closed_at - cl.shipped_at) * cl.amount) / SUM(cl.amount), 1) AS weighted_days_to_pay,
       ROUND(SUM((cl.closed_at - cl.shipped_at) * cl.amount) / SUM(cl.amount)
             - AVG(c.payment_terms_days), 1)                                AS extra_days
FROM closed cl
JOIN customers c ON c.customer_id = cl.customer_id
GROUP BY ROLLUP (c.segment)
ORDER BY c.segment NULLS LAST;
