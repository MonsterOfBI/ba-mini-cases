-- Бизнес-вопрос: можно ли доверять расчёту? Проверки перед закрытием месяца.
-- 1) Валюта статьи есть в справочнике курсов
SELECT 'нет курсов по валюте' AS проверка, count(*) AS найдено
FROM open_items i WHERE NOT EXISTS (SELECT 1 FROM fx_rates r WHERE r.char_code = i.currency)
UNION ALL
-- 2) На каждую отчётную дату загружен курс именно этой даты (иначе загрузка могла упасть)
SELECT 'нет курса ровно на отчётную дату', count(*)
FROM reporting_dates d CROSS JOIN (SELECT DISTINCT currency FROM open_items) c
WHERE NOT EXISTS (SELECT 1 FROM fx_rates r WHERE r.rate_date = d.report_date AND r.char_code = c.currency)
UNION ALL
-- 3) Авансы не попали в переоценку (BR-02)
SELECT 'аванс в переоценке', count(*)
FROM v_revaluation v JOIN open_items i USING (item_id) WHERE NOT i.is_monetary
UNION ALL
-- 4) Курс события старше 3 дней — подозрительно (BR-03)
SELECT 'курс старше 3 дней', count(*) FROM v_revaluation WHERE event_date - rate_date > 3;

-- Неденежные статьи: показываем отдельно, чтобы бухгалтер видел, что их не забыли, а исключили
SELECT doc_no AS документ, item_type AS тип, account AS счёт, currency AS вал, amount_cur AS сумма,
       'не переоценивается: аванс (BR-02)' AS почему
FROM open_items WHERE NOT is_monetary ORDER BY item_id;
