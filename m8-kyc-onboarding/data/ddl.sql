-- Онлайн-открытие счёта ИП в банке «Пример». PostgreSQL 16.
-- Запуск из корня репозитория:  psql -d m8 -f data/ddl.sql && psql -d m8 -f data/load.sql
DROP TABLE IF EXISTS app_events;
DROP TABLE IF EXISTS applications;

-- Заявка = одна попытка открыть счёт. Атрибуты проверок записаны в момент заявки.
CREATE TABLE applications (
    app_id          int PRIMARY KEY,
    created_at      timestamp   NOT NULL,                 -- клиент начал заявку
    device          text        NOT NULL CHECK (device IN ('mobile', 'desktop')),
    inn             char(12)    NOT NULL,                 -- синтетический ИНН с регионом 00
    ip_reg_days     int         NOT NULL,                 -- сколько дней назад зарегистрирован ИП
    okved           text        NOT NULL,                 -- основной ОКВЭД из ЕГРИП
    okved_watch     boolean     NOT NULL,                 -- ОКВЭД из списка «повышенного внимания» банка
    zsk_group       text        NOT NULL CHECK (zsk_group IN ('low', 'medium', 'high', 'none')), -- группа риска ЦБ «Знай своего клиента»
    in_lists        boolean     NOT NULL,                 -- есть в перечне Росфинмониторинга / решении МВК о заморозке
    egrip_status    text        NOT NULL CHECK (egrip_status IN ('active', 'ceased')),
    passport_valid  boolean     NOT NULL,                 -- паспорт действителен (проверка МВД)
    form_mismatch   boolean     NOT NULL,                 -- AS-IS: анкета, набранная руками, не совпала с паспортом/ЕГРИП
    real_mismatch   boolean     NOT NULL,                 -- расхождение настоящее (сменил паспорт, ЕГРИП не обновлён)
    has_ebs         boolean     NOT NULL,                 -- у клиента есть подтверждённая биометрия в ЕБС
    is_risky        boolean     NOT NULL,                 -- ground truth для обучения: заявку надо было остановить
    route_as_is     text        CHECK (route_as_is IN ('auto', 'manual', 'refuse')), -- NULL: не дошёл до проверок
    final_status    text        NOT NULL CHECK (final_status IN ('opened', 'refused', 'abandoned'))
);

-- Журнал шагов заявки (event log). Одна строка — одно событие.
CREATE TABLE app_events (
    event_id   int PRIMARY KEY,
    app_id     int       NOT NULL REFERENCES applications,
    step       text      NOT NULL CHECK (step IN ('started', 'form_submitted', 'upload_error', 'docs_uploaded',
                         'checks_done', 'review_started', 'review_done', 'info_provided', 'identified',
                         'account_opened', 'refused', 'abandoned')),
    event_at   timestamp NOT NULL,
    detail     text      -- причина ошибки, маршрут, решение, способ идентификации, шаг, на котором бросили
);
CREATE INDEX ON app_events (app_id, step);

COMMENT ON COLUMN app_events.event_at IS 'для abandoned — момент закрытия по таймауту 14 дней';
