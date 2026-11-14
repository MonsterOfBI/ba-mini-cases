"""Синтетический реестр валютных статей ООО «Василёк-Импорт» (учебная компания) за сентябрь–октябрь 2026.

Каждая строка — документ: долг покупателя, долг поставщику, аванс или остаток на валютном счёте.
seed фиксирован, поэтому файл всегда одинаковый. Запуск: python data/generate_items.py
"""
import random
from pathlib import Path

import pandas as pd

random.seed(2026)
OUT = Path(__file__).resolve().parent / "open_items.csv"

OP_DATES = ["2026-09-15", "2026-09-30", "2026-10-07", "2026-10-22"]
LATER = {d: [x for x in OP_DATES if x > d] for d in OP_DATES}
SUPPLIERS = {"CNY": ["Шанхай Тулз Ко (учеб.)", "Нинбо Пэкидж (учеб.)", "Гуанчжоу Лайт (учеб.)"],
             "EUR": ["Мюллер Махинен (учеб.)", "Брюгге Фуд (учеб.)"],
             "USD": ["Дельта Трейд (учеб.)"]}
BUYERS = {"USD": ["Алматы Снаб (учеб.)", "Ташкент Строй (учеб.)"], "EUR": ["Рига Опт (учеб.)"], "CNY": ["Харбин Маркет (учеб.)"]}
# тип: (счёт учёта, монетарная ли статья, сторона баланса)
TYPES = {
    "payable":          ("60.21", True,  "liability"),   # долг поставщику
    "receivable":       ("62.21", True,  "asset"),       # долг покупателя
    "advance_paid":     ("60.22", False, "asset"),       # мы заплатили аванс — не переоценивается
    "advance_received": ("62.22", False, "liability"),   # нам заплатили аванс — не переоценивается
}

rows, n = [], 0


def add(kind, cur, cp, amount, rec, settled):
    global n
    n += 1
    acc, monetary, side = TYPES[kind]
    rows.append({"item_id": n, "doc_no": f"{'ПТ' if 'pay' in kind or kind == 'advance_paid' else 'РЛ'}-{1000 + n}",
                 "item_type": kind, "account": acc, "is_monetary": monetary, "side": side,
                 "counterparty": cp, "currency": cur, "amount_cur": round(amount, 2),
                 "recognized_on": rec, "settled_on": settled})


for _ in range(18):                       # поставки от поставщиков: больше всего юаней
    cur = random.choices(["CNY", "EUR", "USD"], weights=[6, 3, 1])[0]
    rec = random.choice(OP_DATES[:3])
    settled = random.choice(LATER[rec] + [None, None])
    amount = random.uniform(150_000, 2_500_000) if cur == "CNY" else random.uniform(8_000, 120_000)
    add("payable", cur, random.choice(SUPPLIERS[cur]), amount, rec, settled)
for _ in range(8):                        # экспорт: долги покупателей
    cur = random.choices(["USD", "EUR", "CNY"], weights=[5, 2, 1])[0]
    rec = random.choice(OP_DATES[:3])
    settled = random.choice(LATER[rec] + [None])
    amount = random.uniform(10_000, 90_000) if cur != "CNY" else random.uniform(100_000, 600_000)
    add("receivable", cur, random.choice(BUYERS[cur]), amount, rec, settled)
for kind, cur in [("advance_paid", "CNY"), ("advance_paid", "EUR"), ("advance_received", "USD")]:
    add(kind, cur, random.choice((SUPPLIERS if kind == "advance_paid" else BUYERS)[cur]),
        random.uniform(20_000, 400_000) if cur == "CNY" else random.uniform(5_000, 30_000), "2026-09-15", None)

df = pd.DataFrame(rows)
df.to_csv(OUT, index=False)
print(f"{len(df)} статей → {OUT.name}")
print(df.groupby(["item_type", "currency"]).amount_cur.agg(["count", "sum"]).round(2))
