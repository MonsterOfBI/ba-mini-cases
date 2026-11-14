"""Генератор синтетической дебиторки ООО «Ромашка-Опт» (январь–октябрь 2026, отчётная дата 31.10.2026).
Запуск:  python data/generate_data.py   → создаёт data/seed.sql и data/sales_sample.csv
Компании и люди вымышленные. random.seed фиксирован — при каждом запуске одни и те же данные.

Пять «типов» клиентов задают поведение, которое потом находят SQL-запросы:
  good       — платят в срок ±3 дня
  late       — стабильно опаздывают на 5–35 дней
  worsening  — опоздание растёт месяц к месяцу (сигнал риска, ловим через LAG)
  partial    — платят частями: 50–70 % сразу, остаток позже или никогда
  default    — с середины июля перестают платить (кандидаты в претензию и суд)
"""
import csv, random
from datetime import date, timedelta
from pathlib import Path

random.seed(2026)
OUT = Path(__file__).parent
REPORT_DATE = date(2026, 10, 31)
START = date(2026, 1, 5)

PREFIX = ["Продукты", "Магазин", "Лавка", "Маркет", "Гастроном", "Кафе", "Столовая", "Сеть"]
NAMES = ["Берёзка", "Уголок", "Колос", "Звезда", "Семь шагов", "Ласточка", "Север", "Полянка", "Радуга",
         "Огонёк", "Пчёлка", "Дубрава", "Каштан", "Восток", "Причал", "Визит", "Сосед", "Хлебница", "Фасоль",
         "Корзинка", "Лукошко", "Ярмарка", "Самовар", "Терем", "Жемчуг", "Пекарня №1", "Изюм", "Мята", "Клён",
         "Бульвар", "Рябина", "Маяк", "Орбита", "Луч", "Улыбка", "Апельсин", "Брусника", "Горница", "Калина", "Вишня"]
OWNERS = ["Иванова Т. С.", "Кравцов Д. И.", "Лебедева О. А.", "Мухин С. В.", "Назарова Е. П.", "Тихонов А. Р.",
          "Фролов К. Н.", "Яковлева И. Г.", "Беляев Р. М.", "Ершова А. В.", "Гордеев П. С.", "Соколова Н. Ю.",
          "Шубин В. А.", "Ткач М. Е.", "Ушакова Д. Л.", "Пронин Г. О.", "Козлова В. Ф.", "Дьячков Л. И."]
MANAGERS = ["Орлова М. Д.", "Семёнов П. А.", "Зайцева Л. В."]
TYPES = ["good"] * 18 + ["late"] * 10 + ["worsening"] * 5 + ["partial"] * 4 + ["default"] * 3
random.shuffle(TYPES)
random.shuffle(OWNERS)


def q(v):
    if v is None:
        return "NULL"
    if isinstance(v, (int, float)):
        return str(v)
    return "'" + str(v).replace("'", "''") + "'"


customers, docs, receipts, actions = [], [], [], []
for cid, (name, ctype) in enumerate(zip(NAMES, TYPES), start=1):
    pref = random.choice(PREFIX)
    segment = "сеть" if pref == "Сеть" else ("HoReCa" if pref in ("Кафе", "Столовая") else "магазин")
    org = "ООО" if segment == "сеть" else random.choice(["ООО", "ООО", "ИП"])
    full = f"ООО «{pref} {name}»" if org == "ООО" else f"ИП {OWNERS.pop(0)} ({pref.lower()} «{name}»)"
    inn = f"77{cid:08d}" if org == "ООО" else f"77{cid:010d}"
    terms = random.choice([14, 14, 21, 30, 30, 45]) if segment != "сеть" else 45
    limit = random.choice([300_000, 500_000, 800_000, 1_200_000]) * (3 if segment == "сеть" else 1)
    customers.append((cid, full, inn, segment, terms, limit, random.choice(MANAGERS), ctype))

doc_id = rec_id = act_id = 0
for c in customers:
    cid, _, _, segment, terms, _, manager, ctype = c
    d = START + timedelta(days=random.randint(0, 10))
    freq = 7 if segment == "сеть" else random.choice([7, 10, 14])
    while d <= REPORT_DATE - timedelta(days=1):
        doc_id += 1
        base = 260_000 if segment == "сеть" else 85_000
        amount = round(random.lognormvariate(0, 0.45) * base * (1 + (d.month - 1) * 0.02), -2)
        due = d + timedelta(days=terms)
        docs.append((doc_id, cid, f"УПД-{doc_id:05d}", d.isoformat(), due.isoformat(), amount))

        # --- когда и сколько заплатил клиент ---
        m = d.month
        pays = []  # список (дата, сумма)
        if ctype == "good":
            pays = [(due + timedelta(days=random.randint(-3, 3)), amount)]
        elif ctype == "late":
            pays = [(due + timedelta(days=random.randint(5, 35)), amount)]
        elif ctype == "worsening":
            pays = [(due + timedelta(days=max(-2, (m - 1) * 5 + random.randint(-3, 4))), amount)]
        elif ctype == "partial":
            first = round(amount * random.uniform(0.5, 0.7), -2)
            pays = [(due + timedelta(days=random.randint(0, 6)), first)]
            if random.random() < 0.8:
                pays.append((due + timedelta(days=random.randint(20, 45)), round(amount - first, 2)))
        elif ctype == "default":
            if d < date(2026, 7, 15):
                pays = [(due + timedelta(days=random.randint(0, 12)), amount)]
            elif random.random() < 0.15:  # изредка «показательный» частичный платёж
                pays = [(due + timedelta(days=random.randint(10, 30)), round(amount * 0.3, -2))]
        pays = [(p, a) for p, a in pays if p <= REPORT_DATE]   # будущих платежей мы ещё не знаем
        for p, a in pays:
            rec_id += 1
            receipts.append((rec_id, doc_id, p.isoformat(), a))

        # --- AS-IS: напоминания «когда вспомнили» ---
        last_pay = max([p for p, _ in pays], default=None)
        fully_paid = abs(sum(a for _, a in pays) - amount) < 0.01
        closed_at = last_pay if fully_paid else REPORT_DATE
        if closed_at > due:  # долг был просрочен хотя бы день
            if random.random() < 0.45:
                r = due + timedelta(days=random.randint(1, 20))
                if r < closed_at:
                    act_id += 1
                    actions.append((act_id, doc_id, "reminder", r.isoformat(), manager))
            if random.random() < 0.25:
                r = due + timedelta(days=random.randint(10, 30))
                if r < closed_at:
                    act_id += 1
                    actions.append((act_id, doc_id, "call", r.isoformat(), manager))
            if ctype == "default" and random.random() < 0.3:
                r = due + timedelta(days=random.randint(45, 70))
                if r < closed_at:
                    act_id += 1
                    actions.append((act_id, doc_id, "claim", r.isoformat(), "Юрист Гусев Р. О."))
        d += timedelta(days=freq + random.randint(-2, 2))

with open(OUT / "seed.sql", "w", encoding="utf-8") as f:
    f.write("-- Сгенерировано data/generate_data.py (seed 2026). Не править руками.\nBEGIN;\n")
    for c in customers:
        f.write(f"INSERT INTO customers VALUES ({', '.join(q(v) for v in c[:7])});\n")
    for row in docs:
        f.write(f"INSERT INTO sales_docs VALUES ({', '.join(q(v) for v in row)});\n")
    for row in receipts:
        f.write(f"INSERT INTO receipts VALUES ({', '.join(q(v) for v in row)});\n")
    for row in actions:
        f.write(f"INSERT INTO collection_actions VALUES ({', '.join(q(v) for v in row)});\n")
    f.write("COMMIT;\n")

with open(OUT / "sales_sample.csv", "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f)
    w.writerow(["doc_id", "customer_id", "doc_no", "shipped_at", "due_date", "amount"])
    w.writerows(docs[:40])

print(f"customers={len(customers)} docs={len(docs)} receipts={len(receipts)} actions={len(actions)}")
