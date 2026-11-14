# Как повторить запрос в SoapUI

1. Установи [SoapUI Open Source](https://www.soapui.org/downloads/soapui/) (бесплатно).
2. **File → New SOAP Project**. Initial WSDL: `https://www.cbr.ru/DailyInfoWebServ/DailyInfo.asmx?WSDL`. Галочка «Create Requests» — включена.
3. В дереве слева: `DailyInfoSoap` → `KeyRateXML` → `Request 1`. SoapUI сам соберёт конверт по WSDL — сравни его с [keyrate-request.xml](keyrate-request.xml).
4. Заполни `fromDate` и `ToDate` в формате `2025-01-01T00:00:00` и нажми зелёный треугольник.
5. Справа появится ответ: внутри `KeyRateXMLResult` — элементы `<KR><DT>…</DT><Rate>…</Rate></KR>`.
6. Сохрани ответ (правый клик → Save) и разбери его: `python scripts/fetch_key_rate.py --file путь/к/ответу.xml`.

## Что посмотреть в WSDL (спросят на собеседовании)
| Раздел WSDL | Что в нём |
|---|---|
| `types` | XSD-схемы параметров и ответов: `fromDate`, `ToDate` — `s:dateTime` |
| `message` | Входящее и исходящее сообщение каждого метода |
| `portType` | Список операций (KeyRate, KeyRateXML, GetCursOnDate…) |
| `binding` | Как передавать: SOAP 1.1 или 1.2, `soapAction` |
| `service` | Адрес, куда слать запрос |

Разница `KeyRate` и `KeyRateXML`: первый возвращает DataSet .NET (схема + diffgram, громоздко), второй — чистый XML. Берём второй.

**Не проверено живым запросом:** cbr.ru из среды сборки проекта недоступен. Конверт собран по описанию сервиса ЦБ; при первом запуске сверь его с тем, что сгенерирует SoapUI.
