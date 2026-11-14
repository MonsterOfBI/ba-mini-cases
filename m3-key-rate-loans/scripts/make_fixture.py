"""Собирает образец ответа KeyRateXML (soap/keyrate-response.sample.xml) из data/key_rate_decisions.csv.

Зачем: сеть, где собирался проект, не пускала на cbr.ru, а проект должен работать без сети.
Ответ сервиса содержит строку на каждый рабочий день; здесь рабочие дни = пн–пт (праздники не учтены).
Сверка с настоящим ответом: bash soap/keyrate.sh > soap/keyrate-response.xml && python scripts/fetch_key_rate.py --file soap/keyrate-response.xml
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
dec = pd.read_csv(ROOT / "data" / "key_rate_decisions.csv", parse_dates=["effective_from"])
days = pd.bdate_range("2024-12-02", "2026-11-13")
rate = pd.Series(dec.rate.values, index=dec.effective_from).reindex(days.union(dec.effective_from)).ffill().loc[days]
rows = "".join(f"<KR><DT>{d:%Y-%m-%d}T00:00:00+03:00</DT><Rate>{r:.2f}</Rate></KR>" for d, r in rate.items())
xml = ('<?xml version="1.0" encoding="utf-8"?>\n'
       '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" '
       'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">'
       '<soap:Body><KeyRateXMLResponse xmlns="http://web.cbr.ru/"><KeyRateXMLResult>'
       f'<KeyRate xmlns="">{rows}</KeyRate>'
       '</KeyRateXMLResult></KeyRateXMLResponse></soap:Body></soap:Envelope>\n')
(ROOT / "soap" / "keyrate-response.sample.xml").write_text(xml, encoding="utf-8")
print(f"{len(rate)} рабочих дней, {rate.iloc[0]}% → {rate.iloc[-1]}%")
