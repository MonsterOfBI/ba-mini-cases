#!/usr/bin/env bash
# Тот же SOAP-запрос через curl (без SoapUI). Запуск из корня: bash soap/keyrate.sh > soap/keyrate-response.xml
curl -sS https://www.cbr.ru/DailyInfoWebServ/DailyInfo.asmx \
  -H 'Content-Type: text/xml; charset=utf-8' \
  -H 'SOAPAction: "http://web.cbr.ru/KeyRateXML"' \
  --data-binary @soap/keyrate-request.xml
