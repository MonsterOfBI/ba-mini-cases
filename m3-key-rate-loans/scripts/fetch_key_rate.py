"""Ключевая ставка ЦБ по SOAP (DailyInfo.KeyRateXML) → data/key_rate.csv.

Что делает: отправляет SOAP-конверт из soap/keyrate-request.xml, достаёт из ответа пары «дата — ставка»
и сохраняет одну строку на день. Без сети читает сохранённый ответ.

Запуск:
    python scripts/fetch_key_rate.py                          # офлайн: soap/keyrate-response.sample.xml
    python scripts/fetch_key_rate.py --live                   # онлайн: запрос к cbr.ru
    python scripts/fetch_key_rate.py --file ответ.xml         # разобрать ответ, сохранённый из SoapUI
Нужно: pip install pandas lxml requests
"""
import argparse
from pathlib import Path

import pandas as pd
from lxml import etree

ROOT = Path(__file__).resolve().parents[1]
URL = "https://www.cbr.ru/DailyInfoWebServ/DailyInfo.asmx"
HEADERS = {"Content-Type": "text/xml; charset=utf-8", "SOAPAction": '"http://web.cbr.ru/KeyRateXML"'}
SOAP_NS = "http://schemas.xmlsoap.org/soap/envelope/"


def call_cbr() -> bytes:
    import requests
    body = (ROOT / "soap" / "keyrate-request.xml").read_bytes()
    r = requests.post(URL, data=body, headers=HEADERS, timeout=30)
    r.raise_for_status()                 # SOAP-ошибка приходит как HTTP 500 с <soap:Fault>
    return r.content


def parse(xml: bytes) -> pd.DataFrame:
    doc = etree.fromstring(xml)
    fault = doc.find(f".//{{{SOAP_NS}}}Fault")
    if fault is not None:
        raise RuntimeError("SOAP Fault: " + "".join(fault.itertext()))
    rows = [{"rate_date": kr.findtext("DT")[:10], "key_rate": float(kr.findtext("Rate"))}
            for kr in doc.iter("KR")]       # KR без пространства имён (xmlns="")
    if not rows:
        raise RuntimeError("В ответе нет элементов KR — проверь период и метод")
    return pd.DataFrame(rows).drop_duplicates("rate_date").sort_values("rate_date")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--file", default=str(ROOT / "soap" / "keyrate-response.sample.xml"))
    a = ap.parse_args()
    xml = call_cbr() if a.live else Path(a.file).read_bytes()
    df = parse(xml)
    df.to_csv(ROOT / "data" / "key_rate.csv", index=False)
    changes = df[df.key_rate != df.key_rate.shift()]
    print(f"{len(df)} дней с {df.rate_date.iloc[0]} по {df.rate_date.iloc[-1]}; изменения ставки:")
    print(changes.to_string(index=False))


if __name__ == "__main__":
    main()
