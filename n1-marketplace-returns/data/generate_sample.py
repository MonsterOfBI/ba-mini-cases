"""Синтетическая выборка В СХЕМЕ Olist — чтобы запросы запускались без скачивания датасета.
Цифры на ней НЕ равны цифрам настоящего Olist. Запуск: python data/generate_sample.py → data/sample_seed.sql"""
import random, hashlib
from datetime import datetime, timedelta
from pathlib import Path
R = random.Random(11)
h = lambda s: hashlib.md5(s.encode()).hexdigest()
STATES = ["SP", "RJ", "MG", "RS", "PR", "BA", "CE", "PE"]
FAR = {"BA", "CE", "PE"}
q = lambda v: "NULL" if v is None else (str(v) if isinstance(v, (int, float)) else "'" + str(v).replace("'", "''") + "'")
rows = []
sellers = [h(f"s{i}") for i in range(40)]
for i, s in enumerate(sellers):
    rows.append(f"INSERT INTO sellers VALUES ({q(s)}, '0{i:04d}', 'city{i}', {q(R.choice(STATES[:5]))});")
start = datetime(2017, 6, 1)
for i in range(3000):
    c, o = h(f"c{i}"), h(f"o{i}")
    st = R.choices(STATES, [40, 13, 12, 6, 6, 8, 7, 8])[0]
    rows.append(f"INSERT INTO customers VALUES ({q(c)}, {q(h('u' + str(i)))}, '1{i:04d}', 'city', {q(st)});")
    buy = start + timedelta(minutes=R.randrange(0, 365 * 24 * 60))
    est = buy + timedelta(days=R.randint(15, 30))
    status = R.choices(["delivered", "shipped", "canceled", "unavailable"], [94, 3, 2, 1])[0]
    seller = R.choice(sellers)
    slow_seller = sellers.index(seller) < 6        # 6 продавцов систематически отгружают поздно
    carrier = buy + timedelta(days=R.randint(1, 4) + (R.randint(3, 8) if slow_seller else 0))
    transit = R.randint(5, 14) + (R.randint(4, 12) if st in FAR else 0)
    delivered = carrier + timedelta(days=transit) if status == "delivered" else None
    rows.append(f"INSERT INTO orders VALUES ({q(o)}, {q(c)}, {q(status)}, {q(buy)}, {q(buy + timedelta(hours=2))}, "
                f"{q(carrier if status in ('delivered', 'shipped') else None)}, {q(delivered)}, {q(est)});")
    price = round(R.lognormvariate(4.3, 0.8), 2)
    rows.append(f"INSERT INTO order_items VALUES ({q(o)}, 1, {q(h('p' + str(i % 500)))}, {q(seller)}, {q(buy + timedelta(days=3))}, {price}, {round(price * R.uniform(0.1, 0.3), 2)});")
    late = delivered is not None and delivered > est
    score = R.choices([1, 2, 3, 4, 5], [45, 15, 15, 12, 13] if late else [6, 3, 8, 20, 63])[0]
    if status != "delivered":
        score = R.choices([1, 2, 3], [70, 20, 10])[0]
    msg = R.choice(["produto com defeito", "não recebi", "veio errado", None]) if score <= 2 else None
    rows.append(f"INSERT INTO order_reviews VALUES ({q(h('r' + str(i)))}, {q(o)}, {score}, NULL, {q(msg)}, {q((delivered or est) + timedelta(days=1))}, NULL);")
Path(__file__).with_name("sample_seed.sql").write_text("BEGIN;\n" + "\n".join(rows) + "\nCOMMIT;\n", encoding="utf-8")
print(len(rows), "rows")
