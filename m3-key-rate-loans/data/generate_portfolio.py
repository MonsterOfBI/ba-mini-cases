"""Синтетический портфель кредитов с плавающей ставкой учебного банка «Колосок» (банк вымышленный).

80 кредитов малому и среднему бизнесу: ставка = ключевая ставка ЦБ + маржа, у части есть пол и потолок.
seed фиксирован. Запуск: python data/generate_portfolio.py
"""
import random
from datetime import date
from pathlib import Path

import pandas as pd

random.seed(77)
OUT = Path(__file__).resolve().parent / "loans.csv"
WORDS1 = ["Северный", "Речной", "Луговой", "Кедровый", "Озёрный", "Степной", "Полевой", "Горный", "Лесной", "Приморский"]
WORDS2 = ["Завод", "Склад", "Хлеб", "Металл", "Пласт", "Транс", "Агро", "Строй", "Опт", "Сервис"]

rows = []
for i in range(1, 81):
    segment = random.choices(["МСБ", "Средний"], weights=[3, 1])[0]
    issue = date(random.choice([2024, 2025, 2025, 2026]), random.randint(1, 12), 1)
    if issue > date(2026, 6, 1):
        issue = issue.replace(year=2025)
    term = random.choice([24, 36, 48, 60])
    principal = round(random.uniform(5, 60) if segment == "МСБ" else random.uniform(60, 300), 1) * 1_000_000
    margin = round(random.choice([1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0, 6.0]), 2)
    has_floor = random.random() < 0.6           # банк защищается от падения ставки
    has_cap = random.random() < 0.35            # клиент защищается от роста ставки
    floor = round(random.choice([15.0, 16.0, 17.0, 18.0, 19.0]), 2) if has_floor else None
    cap = round(random.choice([23.0, 24.0, 25.0, 26.0]), 2) if has_cap else None
    if floor and cap and cap <= floor:
        cap = None
    rows.append({"loan_id": i, "contract_no": f"КЛ-{2400 + i}",
                 "client": f"ООО «{random.choice(WORDS1)} {random.choice(WORDS2)}» (учеб.)",
                 "segment": segment, "issue_date": issue.isoformat(), "term_months": term,
                 "principal": principal, "margin_pp": margin, "floor_pct": floor, "cap_pct": cap,
                 "notify_channel": random.choice(["ДБО", "ДБО", "email", "ДБО+звонок"])})

df = pd.DataFrame(rows)
df.to_csv(OUT, index=False)
print(f"{len(df)} кредитов, {df.principal.sum() / 1e9:.2f} млрд ₽; с полом {df.floor_pct.notna().sum()}, с потолком {df.cap_pct.notna().sum()}")
