"""Генератор синтетических карточных операций для кейса «Кэшбэк по MCC» (август–октябрь 2026).
Запуск:  pip install pandas faker   →   python data/generate_data.py
Создаёт: data/mcc_groups.csv, data/clients.csv, data/merchants.csv, data/client_categories.csv,
         data/transactions.csv (+ transactions_sample.csv).
Банк «Пример», клиенты и магазины вымышленные; имена — из Faker (ru_RU), совпадения случайны.
Сиды фиксированы (random, numpy, Faker) — при каждом запуске одни и те же данные.

Что специально заложено, чтобы аналитике было что найти:
  * «умные» клиенты выбирают повышенные категории там, где тратят больше всего (это и раздувает стоимость);
  * часть кафе работает внутри супермаркетов и получила MCC 5411 — повод для жалоб «кэшбэк не начислили»;
  * мелкие покупки до 100 ₽, исключённые MCC (переводы, наличные, ЖКУ), возвраты покупок.
"""
from datetime import date, timedelta
from pathlib import Path
import random

import numpy as np
import pandas as pd
from faker import Faker

SEED = 606
random.seed(SEED)
np.random.seed(SEED)
Faker.seed(SEED)
fake = Faker("ru_RU")
OUT = Path(__file__).parent
MONTHS = [date(2026, 8, 1), date(2026, 9, 1), date(2026, 10, 1)]

# Справочник групп MCC. elevated_rate — ставка, если клиент выбрал категорию в этом месяце; None — выбрать нельзя.
# is_excluded — кэшбэк не начисляется совсем (наличные, переводы, квази-кэш, ЖКУ, госплатежи, азартные игры).
GROUPS = {
    # код:          (название,                 MCC,                                   elevated, excluded)
    "supermarkets": ("Супермаркеты",           [5411, 5499],                          0.03, False),
    "restaurants":  ("Кафе и рестораны",       [5812, 5813, 5814],                    0.05, False),
    "fuel":         ("АЗС",                    [5541, 5542],                          0.05, False),
    "taxi":         ("Такси и каршеринг",      [4121, 7512],                          0.05, False),
    "pharmacy":     ("Аптеки",                 [5912],                                0.05, False),
    "clothing":     ("Одежда и обувь",         [5651, 5661, 5691],                    0.05, False),
    "electronics":  ("Электроника",            [5732],                                None, False),
    "marketplace":  ("Маркетплейсы и универмаги", [5311, 5399],                       None, False),
    "travel":       ("Билеты и отели",         [4511, 7011],                          None, False),
    "utilities":    ("ЖКУ",                    [4900],                                None, True),
    "excluded":     ("Наличные, переводы, квази-кэш, госплатежи, игры",
                     [6010, 6011, 6012, 6051, 4829, 6540, 7995, 9311, 9222, 9399],  None, True),
}
# Типичная сумма чека (медиана, ₽) и частота покупок в месяц для «среднего» клиента
SPEND = {
    "supermarkets": (900, 10), "restaurants": (700, 4), "fuel": (2600, 2.2), "taxi": (450, 3),
    "pharmacy": (650, 1.2), "clothing": (3500, 0.6), "electronics": (9000, 0.15), "marketplace": (1600, 3),
    "travel": (14000, 0.08), "utilities": (5200, 1), "excluded": (4000, 1.5),
}
SHOP_WORD = {"supermarkets": "Супермаркет", "restaurants": "Кафе", "fuel": "АЗС", "taxi": "Такси", "pharmacy": "Аптека",
             "clothing": "Магазин одежды", "electronics": "Электроника", "marketplace": "Маркетплейс",
             "travel": "Турагентство", "utilities": "УК", "excluded": "Сервис"}
ELECTABLE = [g for g, v in GROUPS.items() if v[2] is not None]

mcc_rows = []
for code, (name, mccs, elev, excl) in GROUPS.items():
    for m in mccs:
        mcc_rows.append({"mcc": m, "group_code": code, "group_name": name,
                         "elevated_rate": elev, "is_excluded": excl})
mcc_df = pd.DataFrame(mcc_rows)

# Клиенты: доход влияет на объём трат, «водители» тратят на АЗС больше, «умные» выбирают категории по своим тратам
clients = []
for cid in range(1, 1201):
    clients.append({
        "client_id": cid,
        "full_name": fake.name(),
        "city": fake.city_name(),
        "spend_level": round(float(np.random.lognormal(0, 0.55)), 2),
        "is_driver": random.random() < 0.35,
        "is_smart_chooser": random.random() < 0.6,
    })
clients_df = pd.DataFrame(clients)

# Магазины: у каждого один MCC (его присваивает банк-эквайер при подключении к картам)
merchants, mid = [], 0
for code, (name, mccs, _, _) in GROUPS.items():
    n = 40 if code in ("supermarkets", "restaurants", "marketplace") else 15
    for _ in range(n):
        mid += 1
        merchants.append({"merchant_id": mid, "merchant_name": f"{SHOP_WORD[code]} «{fake.last_name()}»",
                          "mcc": random.choice(mccs), "group_code": code})
# Кафе внутри супермаркетов: по смыслу ресторан, но MCC 5411 (эквайер подключил всю точку как магазин)
for _ in range(8):
    mid += 1
    merchants.append({"merchant_id": mid, "merchant_name": f"Кафе «{fake.last_name()}» в гипермаркете",
                      "mcc": 5411, "group_code": "restaurants_in_store"})
merchants_df = pd.DataFrame(merchants)


def merchants_of(group):
    if group == "restaurants" and random.random() < 0.12:
        return merchants_df[merchants_df.group_code == "restaurants_in_store"]
    return merchants_df[merchants_df.group_code == group]


tx, choices, tx_id = [], [], 0
for c in clients:
    for m0 in MONTHS:
        days_in_m = ((m0.replace(day=28) + timedelta(days=4)).replace(day=1) - m0).days
        month_tx = []
        for g, (median, freq) in SPEND.items():
            f = freq * (2.2 if g == "fuel" and c["is_driver"] else (0.3 if g == "fuel" else 1))
            for _ in range(np.random.poisson(f * min(c["spend_level"], 2.5))):
                amount = round(float(np.random.lognormal(np.log(median * c["spend_level"] ** 0.5), 0.6)), 2)
                if g == "supermarkets" and random.random() < 0.08:
                    amount = round(random.uniform(35, 99), 2)   # хлеб и вода: покупки до 100 ₽
                mrow = merchants_of(g).sample(1, random_state=random.randint(0, 10**9)).iloc[0]
                month_tx.append((g, amount, int(mrow.merchant_id), int(mrow.mcc), m0 + timedelta(days=random.randrange(days_in_m))))
        # Выбор двух повышенных категорий на месяц
        if c["is_smart_chooser"]:
            spend_by_g = {g: 0.0 for g in ELECTABLE}
            for g, a, *_ in month_tx:
                if g in spend_by_g:
                    spend_by_g[g] += a * GROUPS[g][2]
            chosen = sorted(spend_by_g, key=spend_by_g.get, reverse=True)[:2]
        else:
            chosen = random.sample(ELECTABLE, 2)
        for g in chosen:
            choices.append({"client_id": c["client_id"], "month": m0.isoformat(), "group_code": g})
        for g, a, merch, mcc, d in month_tx:
            tx_id += 1
            tx.append({"tx_id": tx_id, "client_id": c["client_id"], "merchant_id": merch, "mcc": mcc,
                       "tx_date": d.isoformat(), "amount": a, "tx_type": "purchase", "original_tx_id": None})
            # Возвраты: одежда и электроника чаще, через 3–20 дней (иногда уже в следующем месяце)
            p_ref = {"clothing": 0.12, "electronics": 0.08, "marketplace": 0.05}.get(g, 0.005)
            if random.random() < p_ref:
                rd = d + timedelta(days=random.randint(3, 20))
                if rd <= date(2026, 10, 31):
                    tx_id += 1
                    tx.append({"tx_id": tx_id, "client_id": c["client_id"], "merchant_id": merch, "mcc": mcc,
                               "tx_date": rd.isoformat(), "amount": -a, "tx_type": "refund", "original_tx_id": tx_id - 1})

tx_df = pd.DataFrame(tx)
tx_df["original_tx_id"] = tx_df["original_tx_id"].astype("Int64")
mcc_df.to_csv(OUT / "mcc_groups.csv", index=False)
clients_df.to_csv(OUT / "clients.csv", index=False)
merchants_df.to_csv(OUT / "merchants.csv", index=False)
pd.DataFrame(choices).to_csv(OUT / "client_categories.csv", index=False)
tx_df.to_csv(OUT / "transactions.csv", index=False)
tx_df.head(200).to_csv(OUT / "transactions_sample.csv", index=False)
print(f"clients={len(clients_df)} merchants={len(merchants_df)} tx={len(tx_df)} "
      f"refunds={(tx_df.tx_type == 'refund').sum()} turnover_mln={tx_df[tx_df.amount > 0].amount.sum() / 1e6:.1f}")
