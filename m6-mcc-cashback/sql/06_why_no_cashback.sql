-- Бизнес-вопрос: почему клиенты жалуются «кэшбэк не начислили»? Разбираем покупки с нулевым или урезанным кэшбэком
-- по причинам — это готовый FAQ для поддержки и список задач для продукта.
-- Отдельно ищем магазины, где MCC не совпадает с реальным бизнесом (кафе в гипермаркете с MCC 5411).
SELECT CASE
           WHEN rule_applied LIKE 'CB-01%'                 THEN '1. Исключённый MCC (переводы, наличные, ЖКУ)'
           WHEN rule_applied LIKE 'CB-02%'                 THEN '2. Покупка меньше 100 ₽'
           WHEN cashback < cashback_raw AND cashback = 0   THEN '3. Лимит 3 000 ₽ уже исчерпан'
           WHEN cashback < cashback_raw                    THEN '4. Лимит урезал кэшбэк частично'
       END                                                  AS reason,
       COUNT(*)                                             AS purchases,
       COUNT(DISTINCT client_id)                            AS clients,
       ROUND(SUM(amount) / 1e3)                             AS turnover_thous
FROM v_purchase_cashback
WHERE cashback = 0 OR cashback < cashback_raw
GROUP BY 1
ORDER BY 1;

-- Округление вниз (CB-05) нулей не даёт — минимальная покупка 100 ₽ × 1 % = 1 ₽, — но «съедает» копейки.
-- Клиент, который считает кэшбэк сам, видит расхождение. Сколько это в деньгах:
SELECT ROUND(SUM(amount * rate - FLOOR(amount * rate)) / 3) AS rounding_loss_per_month_rub,
       ROUND(AVG(amount * rate - FLOOR(amount * rate)), 2)  AS avg_loss_per_purchase_rub
FROM v_purchase_cashback WHERE rate > 0;

-- Кандидаты на ошибочный MCC: по названию кафе, по MCC — супермаркет. Клиент выбрал «Кафе и рестораны»,
-- а получил 1 %. Это не ошибка расчёта: MCC присвоил эквайер. Решение — список исключений по ID магазина (CR-2).
SELECT m.merchant_name, m.mcc, g.group_name AS mcc_group,
       COUNT(*) AS purchases,
       COUNT(*) FILTER (WHERE EXISTS (SELECT 1 FROM client_categories cc
                                      WHERE cc.client_id = pc.client_id AND cc.month = pc.month
                                        AND cc.group_code = 'restaurants')) AS by_clients_who_chose_restaurants
FROM v_purchase_cashback pc
JOIN transactions t USING (tx_id)
JOIN merchants m ON m.merchant_id = t.merchant_id
JOIN mcc_groups g ON g.mcc = m.mcc
WHERE m.merchant_name ILIKE 'кафе%' AND g.group_code <> 'restaurants'
GROUP BY m.merchant_name, m.mcc, g.group_name
ORDER BY purchases DESC;
