# Интеграция CRM ↔ 1С: от лида до счёта

> **Учебный мини-кейс.** Компания вымышленная, внедрения не было. Формат — типовая задача с собеседования системного аналитика: «опишите интеграцию CRM с ERP».

**За 30 секунд.** Продажи ведут сделки в CRM, а счета бухгалтерия вбивает в 1С вручную: 15 минут на счёт, ошибки в реквизитах, менеджер не видит оплату. Я описал интеграцию: что и в какую сторону передаётся, как часто, какая система — источник истины по каждому полю, маппинг полей, обмен через очередь с повторами и идемпотентностью, состояния сделки, RACI и обработку ошибок.

## Главное за минуту
| Вопрос интервьюера | Ответ в кейсе |
|---|---|
| Направление и объём | CRM → 1С: клиенты и счета (~600/мес); 1С → CRM: номер счёта, PDF, оплата; номенклатура — раз в сутки |
| Источник истины | Сделка — CRM; реквизиты, цены, счёт, оплата — 1С |
| Синхронно или асинхронно | Асинхронно через очередь: 1С бывает недоступна, менеджеру не нужен мгновенный ответ |
| Дубли | `ВнешнийИД счёта = deal_id`, повтор возвращает существующий счёт |
| Ошибки | 5 повторов с задержкой → dead-letter → задача менеджеру |

## Артефакты
| Файл | Что |
|---|---|
| [docs/integration-spec.md](docs/integration-spec.md) | Вся спецификация: объём, источник истины, маппинг, sequence, состояния, RACI, ошибки, НФТ |
| [uml/invoice-flow.puml](uml/invoice-flow.puml) | Sequence в PlantUML |
| [api/adapter-openapi.yaml](api/adapter-openapi.yaml) | Мини-контракт обратной связи 1С → CRM (валидирован) |

## Ключевое решение
Реквизиты юрлица после создания правятся только в 1С, в CRM они только для чтения. Иначе две системы будут перезаписывать друг друга, и счета уйдут со старым КПП.

## Как сделано
Учебный проект с ИИ-ассистентом (Claude) как ревьюером. Что я сделал сам — [DEFENSE.md](DEFENSE.md).

---
## English summary
Learning mini-project framed as a classic system analyst interview task: integrate a CRM with 1C (ERP) from lead to invoice. The spec covers data flows and volumes, source of truth per field, field mapping, an asynchronous queue-based exchange with retries, dead-letter handling and idempotency via an external invoice ID, deal state transitions, RACI and non-functional requirements, plus a small OpenAPI contract for callbacks from 1C to the CRM.
