"""Генератор синтетических операций мобильного кошелька в формате набора PaySim (30 дней, 720 часов).
Запуск:  python data/generate_data.py   → data/transactions.csv (≈45 тыс. строк) и data/transactions_sample.csv
Колонки те же, что в PaySim (Kaggle «Synthetic Financial Datasets For Fraud Detection»), поэтому все SQL
из папки sql/ можно прогнать и на настоящем PaySim — см. data/SOURCES.md.
Клиенты вымышленные, идентификаторы условные (C… — клиент, M… — магазин). random.seed фиксирован.

Схема мошенничества как в PaySim: злоумышленник захватывает кошелёк, переводит деньги (TRANSFER) на счёт
«дропа» и тут же выводит их наличными (CASH_OUT). Чтобы правилам было что «шуметь», добавлены
легальные крупные переводы, ночные операции и переводы «всё на свой счёт в другом банке».
"""
import csv, random
from pathlib import Path

random.seed(55)
OUT = Path(__file__).parent
HOURS = 720
N_CLIENTS = 6000
N_LEGIT = 44000
N_FRAUD = 140

balance = {f"C{100000 + i}": round(random.lognormvariate(10.6, 1.0), 2) for i in range(N_CLIENTS)}
clients = list(balance)
merchants = [f"M{500000 + i}" for i in range(800)]
dest_balance = {}  # балансы получателей переводов (клиентов)
rows = []


def hour_of_step():
    """Дневная сезонность: ночью операций мало."""
    while True:
        step = random.randint(1, HOURS)
        h = (step - 1) % 24
        if random.random() < (0.15 if h < 6 else 1.0):
            return step


def add(step, typ, amount, orig, dest, is_fraud, dest_untouched=False):
    amount = round(min(amount, 10_000_000), 2)
    ob = balance.get(orig, 0.0)
    if typ != "CASH_IN" and not is_fraud and amount > ob:
        ob = round(amount * random.uniform(1.2, 3.0), 2)   # перед тратой клиент пополнил кошелёк
    if typ in ("PAYMENT", "TRANSFER", "CASH_OUT", "DEBIT"):
        amount = min(amount, ob) if ob > 0 else amount
        nb = round(max(ob - amount, 0), 2)
    else:  # CASH_IN
        nb = round(ob + amount, 2)
    balance[orig] = nb
    if dest.startswith("M"):
        odb = ndb = 0.0                         # у магазинов баланс в PaySim не ведётся
    elif dest_untouched:
        odb = ndb = 0.0                         # особенность PaySim: у счёта дропа балансы нулевые
    else:
        odb = dest_balance.get(dest, round(random.lognormvariate(10, 1.2), 2))
        ndb = round(odb + amount, 2)
        dest_balance[dest] = ndb
    rows.append([step, typ, amount, orig, round(ob, 2), nb, dest, odb, ndb, is_fraud,
                 1 if typ == "TRANSFER" and amount > 10_000_000 else 0])


events = []
for _ in range(N_LEGIT):
    step = hour_of_step()
    typ = random.choices(["PAYMENT", "TRANSFER", "CASH_OUT", "CASH_IN", "DEBIT"], [34, 9, 35, 21, 1])[0]
    orig = random.choice(clients)
    if typ == "PAYMENT":
        events.append((step, typ, random.lognormvariate(7.5, 1.0), orig, random.choice(merchants), 0, False))
    elif typ == "TRANSFER":
        r = random.random()
        if r < 0.04:      # «перевожу всё на свой счёт в другом банке» — легально, но похоже на обнуление
            amt = balance[orig]
        elif r < 0.07:    # крупная легальная покупка (машина, ремонт)
            amt = random.uniform(200_000, 900_000)
        else:
            amt = random.lognormvariate(9.6, 1.1)
        dest = random.choice(clients)
        new_dest = random.random() < 0.25   # перевод на новый счёт без истории
        events.append((step, typ, amt, orig, dest if not new_dest else f"C9{random.randint(10**6, 10**7)}", 0, new_dest))
    elif typ == "CASH_OUT":
        events.append((step, typ, random.lognormvariate(9.3, 1.0), orig, random.choice(merchants), 0, False))
    elif typ == "CASH_IN":
        events.append((step, typ, random.lognormvariate(9.5, 1.0), orig, random.choice(merchants), 0, False))
    else:
        events.append((step, typ, random.lognormvariate(7, 0.8), orig, random.choice(merchants), 0, False))

# Легальные «серии»: клиент за несколько часов переводит деньги нескольким людям (скинуться на подарок, зарплата помощникам)
for _ in range(60):
    step, orig = hour_of_step(), random.choice(clients)
    for k in range(random.randint(3, 5)):
        events.append((min(step + k, HOURS), "TRANSFER", random.lognormvariate(8.5, 0.8), orig, random.choice(clients), 0, False))

fraud_meta = []
for k in range(N_FRAUD):
    step = random.randint(1, HOURS - 3)
    if random.random() < 0.35:           # мошенники любят ночь
        day = (step - 1) // 24
        step = day * 24 + random.randint(1, 5)
    victim = random.choice(clients)
    mule = f"C8{k:06d}"
    share = 1.0 if random.random() < 0.8 else random.uniform(0.6, 0.9)   # 20 % забирают не всё
    fraud_meta.append((step, victim, mule, share))

# Проигрываем события по времени, чтобы балансы менялись последовательно
timeline = [(e[0], 0, e) for e in events] + [(f[0], 1, f) for f in fraud_meta]
timeline.sort(key=lambda t: (t[0], t[1]))
for step, kind, payload in timeline:
    if kind == 0:
        s, typ, amt, orig, dest, fr, untouched = payload
        add(s, typ, amt, orig, dest, fr, untouched)
    else:
        s, victim, mule, share = payload
        amt = round(max(balance[victim], 15_000) * share, 2)
        if balance[victim] < 15_000:
            balance[victim] = 15_000.0 + random.uniform(0, 50_000)   # жертва только что пополнила кошелёк
            amt = round(balance[victim] * share, 2)
        add(s, "TRANSFER", amt, victim, mule, 1, dest_untouched=True)
        balance[mule] = amt
        delay = random.choice([0, 0, 1, 1, 2, 4, 6])      # иногда дроп выжидает несколько часов
        if random.random() < 0.15:                        # иногда выводит двумя частями
            part = round(amt * random.uniform(0.3, 0.6), 2)
            add(min(s + delay, HOURS), "CASH_OUT", part, mule, random.choice(merchants), 1)
            add(min(s + delay + 1, HOURS), "CASH_OUT", round(amt - part, 2), mule, random.choice(merchants), 1)
        else:
            add(min(s + delay, HOURS), "CASH_OUT", amt, mule, random.choice(merchants), 1)

rows.sort(key=lambda r: r[0])
header = ["step", "type", "amount", "nameOrig", "oldbalanceOrg", "newbalanceOrig",
          "nameDest", "oldbalanceDest", "newbalanceDest", "isFraud", "isFlaggedFraud"]
with open(OUT / "transactions.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(header); w.writerows(rows)
with open(OUT / "transactions_sample.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(header); w.writerows(rows[:200])
print(f"rows={len(rows)} fraud_rows={sum(r[9] for r in rows)}")
