"""Курсы ЦБ (XML_daily.asp) → data/rates.csv.

Что делает: на каждую нужную дату берёт XML ответа ЦБ, проверяет его по XSD,
переводит «84,4283» в число, делит на номинал и складывает всё в одну таблицу.

Запуск:
    python scripts/fetch_rates.py            # офлайн: читает сохранённые ответы из data/cbr_xml/
    python scripts/fetch_rates.py --live     # онлайн: скачивает с cbr.ru и перезаписывает data/cbr_xml/

Нужно: pip install pandas lxml requests
"""
import argparse
from datetime import date
from pathlib import Path

import pandas as pd
from lxml import etree

ROOT = Path(__file__).resolve().parents[1]
XML_DIR = ROOT / "data" / "cbr_xml"
XSD = etree.XMLSchema(etree.parse(str(ROOT / "data" / "schema" / "ValCurs.xsd")))
URL = "https://www.cbr.ru/scripts/XML_daily.asp"

# Какие даты нужны: даты операций и отчётные даты из реестра + все последние числа месяцев
DATES = [date(2026, 9, 15), date(2026, 9, 30), date(2026, 10, 7), date(2026, 10, 22), date(2026, 10, 31)]
CURRENCIES = {"USD", "EUR", "CNY"}


def ru_number(text: str) -> float:
    """ЦБ пишет дробную часть через запятую."""
    return float(text.replace(",", "."))


def download(d: date) -> bytes:
    import requests
    r = requests.get(URL, params={"date_req": d.strftime("%d/%m/%Y")}, timeout=30)
    r.raise_for_status()
    return r.content


def parse(xml_bytes: bytes, requested: date) -> list[dict]:
    doc = etree.fromstring(xml_bytes)          # lxml сам читает encoding="windows-1251"
    XSD.assertValid(doc)                       # упадёт с понятной ошибкой, если ЦБ поменял формат
    rate_date = pd.to_datetime(doc.get("Date"), format="%d.%m.%Y").date()
    rows = []
    for v in doc.findall("Valute"):
        code = v.findtext("CharCode")
        if code not in CURRENCIES:
            continue
        nominal = int(v.findtext("Nominal"))
        value = ru_number(v.findtext("Value"))
        rows.append({
            "requested_date": requested.isoformat(),
            "rate_date": rate_date.isoformat(),   # может отличаться от запрошенной (выходные, праздники)
            "char_code": code,
            "nominal": nominal,
            "value": value,
            "unit_rate": round(value / nominal, 6),  # курс за 1 единицу валюты
        })
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true", help="скачать с cbr.ru")
    args = ap.parse_args()
    rows = []
    for d in DATES:
        f = XML_DIR / f"XML_daily_{d.isoformat()}.xml"
        if args.live:
            f.write_bytes(download(d))
        rows += parse(f.read_bytes(), d)
    df = pd.DataFrame(rows).sort_values(["rate_date", "char_code"])
    shifted = df[df.requested_date != df.rate_date]
    if not shifted.empty:
        print("Внимание: на эти даты ЦБ вернул курс другой даты:\n", shifted[["requested_date", "rate_date"]].drop_duplicates())
    out = ROOT / "data" / "rates.csv"
    df.to_csv(out, index=False)
    print(f"{len(df)} курсов → {out.relative_to(ROOT)}")
    print(df.pivot(index="rate_date", columns="char_code", values="unit_rate"))


if __name__ == "__main__":
    main()
