"""Пишет образцы ответов XML_daily.asp в data/cbr_xml/ — чтобы проект работал без сети.

Значения курсов на 5 дат переписаны со страниц агрегатора myfin.by (он публикует курсы ЦБ),
14.11.2026; с cbr.ru напрямую не сверены — сеть песочницы закрыта. Ответ ЦБ сокращён до 3 валют.
Сверка: python scripts/fetch_rates.py --live  (перезапишет файлы настоящими ответами ЦБ).
"""
from pathlib import Path

RATES = {  # дата: {код: (ID, NumCode, Nominal, Name, Value)}
    "15.09.2026": {"USD": 84.3363, "EUR": 97.7626, "CNY": 12.5353},
    "30.09.2026": {"USD": 84.4283, "EUR": 96.0625, "CNY": 12.5764},
    "07.10.2026": {"USD": 85.7116, "EUR": 96.0313, "CNY": 12.7984},
    "22.10.2026": {"USD": 81.9739, "EUR": 91.9337, "CNY": 12.2806},
    "31.10.2026": {"USD": 80.5573, "EUR": 89.6603, "CNY": 12.0873},
}
META = {"USD": ("R01235", "840", 1, "Доллар США"),
        "EUR": ("R01239", "978", 1, "Евро"),
        "CNY": ("R01375", "156", 1, "Китайский юань")}


def ru(x: float) -> str:
    return f"{x:.4f}".replace(".", ",")


out = Path(__file__).resolve().parents[1] / "data" / "cbr_xml"
out.mkdir(parents=True, exist_ok=True)
for d, vals in RATES.items():
    rows = []
    for code, value in vals.items():
        vid, num, nom, name = META[code]
        rows.append(f'<Valute ID="{vid}"><NumCode>{num}</NumCode><CharCode>{code}</CharCode>'
                    f'<Nominal>{nom}</Nominal><Name>{name}</Name><Value>{ru(value)}</Value>'
                    f'<VunitRate>{ru(value / nom)}</VunitRate></Valute>')
    xml = ('<?xml version="1.0" encoding="windows-1251"?>'
           f'<ValCurs Date="{d}" name="Foreign Currency Market">' + "".join(rows) + "</ValCurs>")
    dd, mm, yy = d.split(".")
    (out / f"XML_daily_{yy}-{mm}-{dd}.xml").write_bytes(xml.encode("cp1251"))
    print("written", d)
