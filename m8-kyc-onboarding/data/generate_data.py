"""Генератор синтетических заявок на онлайн-открытие счёта ИП в банке «Пример» (август–октябрь 2026).

Только стандартная библиотека Python, seed фиксирован: при каждом запуске — те же данные.
Запуск из корня репозитория:  python data/generate_data.py
Результат: data/applications.csv, data/app_events.csv

Что заложено в данные (AS-IS, как процесс работает сейчас):
- 70 % заявок с телефона; на шаге загрузки документов бросают чаще с телефона (фото тяжёлые, размыто,
  банк просит «свидетельство ОГРНИП», которого у ИП после 2017 года нет — есть лист записи ЕГРИП);
- анкету клиент заполняет руками, поэтому в 18 % заявок данные «не совпадают» с паспортом или ЕГРИП
  (опечатки, ё/е, формат адреса), а настоящих расхождений — около 3 %;
- правило AS-IS отправляет на ручную проверку всё, что не идеально: расхождение, ОКВЭД из списка внимания,
  группа ЗСК не «зелёная» или ещё не присвоена;
- ground truth is_risky — «заявка, которую комплаенс должен был остановить»; у «зелёной» группы ЗСК её нет.
ИНН с несуществующим кодом региона 00 и корректной контрольной суммой — совпасть с реальным ИНН не могут.
"""
import csv
import math
import random
from datetime import datetime, timedelta
from pathlib import Path

SEED = 808
N_APPS = 4000
START = datetime(2026, 8, 1)
DAYS = 92  # август–октябрь
OUT = Path(__file__).resolve().parent

OKVED_NORMAL = ["47.91", "62.01", "43.39", "96.02", "49.41", "73.11", "85.41", "56.10", "74.20", "95.11", "86.90", "45.20"]
OKVED_WATCH = ["46.90", "64.99", "66.19", "46.72", "70.22", "82.99"]  # список «повышенного внимания» банка (допущение)

rnd = random.Random(SEED)


def inn_fl():
    """12-значный ИНН физлица/ИП с кодом региона 00 и правильными контрольными цифрами."""
    d = [0, 0] + [rnd.randint(0, 9) for _ in range(8)]
    w11 = [7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
    w12 = [3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
    d.append(sum(a * b for a, b in zip(d, w11)) % 11 % 10)
    d.append(sum(a * b for a, b in zip(d, w12)) % 11 % 10)
    return "".join(map(str, d))


def pick(weights):
    """weights: {значение: вес}"""
    r = rnd.random() * sum(weights.values())
    for k, w in weights.items():
        r -= w
        if r <= 0:
            return k
    return k


def lognorm(median, sigma):
    return median * math.exp(rnd.gauss(0, sigma))


def work_hours_later(t, hours):
    """Сдвиг на hours рабочих часов комплаенса (пн–пт, 9:00–18:00)."""
    left = hours
    while True:
        if t.weekday() >= 5:
            t = (t + timedelta(days=7 - t.weekday())).replace(hour=9, minute=0, second=0)
            continue
        day_start = t.replace(hour=9, minute=0, second=0)
        day_end = t.replace(hour=18, minute=0, second=0)
        if t < day_start:
            t = day_start
        if t >= day_end:
            t = (t + timedelta(days=1)).replace(hour=9, minute=0, second=0)
            continue
        avail = (day_end - t).total_seconds() / 3600
        if left <= avail:
            return t + timedelta(hours=left)
        left -= avail
        t = (t + timedelta(days=1)).replace(hour=9, minute=0, second=0)


def as_is_route(a):
    """Правило маршрутизации, которое работает сейчас (описано в docs/requirements.md, раздел AS-IS)."""
    if a["in_lists"] or not a["passport_valid"] or a["egrip_status"] == "ceased" or a["zsk_group"] == "high":
        return "refuse"
    if a["form_mismatch"] or a["okved_watch"] or a["zsk_group"] in ("medium", "none"):
        return "manual"
    return "auto"


apps, events = [], []
eid = 0


def ev(app_id, step, t, detail=""):
    global eid
    eid += 1
    events.append({"event_id": eid, "app_id": app_id, "step": step,
                   "event_at": t.strftime("%Y-%m-%d %H:%M:%S"), "detail": detail})


for i in range(1, N_APPS + 1):
    day = rnd.randrange(DAYS)
    hour = pick({h: w for h, w in zip(range(24), [1, 1, 1, 1, 1, 2, 3, 5, 7, 9, 10, 10, 9, 9, 9, 9, 9, 9, 10, 11, 11, 9, 6, 3])})
    t0 = START + timedelta(days=day, hours=hour, minutes=rnd.randrange(60), seconds=rnd.randrange(60))
    device = "mobile" if rnd.random() < 0.70 else "desktop"
    zsk = pick({"low": 70, "medium": 8, "high": 2, "none": 20})
    # «нет группы ЗСК» — почти всегда свежий ИП, ЦБ ещё не оценил
    ip_age = rnd.randint(1, 45) if zsk == "none" else rnd.randint(60, 4000)
    okved_watch = rnd.random() < (0.10 if zsk == "low" else 0.25)
    okved = rnd.choice(OKVED_WATCH if okved_watch else OKVED_NORMAL)
    in_lists = rnd.random() < 0.003
    egrip_status = "ceased" if rnd.random() < 0.01 else "active"
    passport_valid = rnd.random() > 0.005
    real_mismatch = rnd.random() < 0.03
    form_mismatch = real_mismatch or rnd.random() < 0.155  # ручной ввод: опечатки, ё/е, формат адреса
    has_ebs = rnd.random() < 0.25
    p_risky = {"low": 0.0, "medium": 0.30, "high": 0.80}.get(zsk)
    if zsk == "none":
        p_risky = 0.30 if okved_watch else 0.04
    is_risky = in_lists or rnd.random() < p_risky

    a = dict(app_id=i, created_at=t0.strftime("%Y-%m-%d %H:%M:%S"), device=device, inn=inn_fl(),
             ip_reg_days=ip_age, okved=okved, okved_watch=okved_watch, zsk_group=zsk, in_lists=in_lists,
             egrip_status=egrip_status, passport_valid=passport_valid, form_mismatch=form_mismatch,
             real_mismatch=real_mismatch, has_ebs=has_ebs, is_risky=is_risky,
             route_as_is="", final_status="")
    apps.append(a)
    ev(i, "started", t0)

    # 1. Анкета: 25 полей руками
    t = t0 + timedelta(minutes=lognorm(9 if device == "desktop" else 13, 0.4))
    if rnd.random() < (0.13 if device == "mobile" else 0.08):
        ev(i, "abandoned", t + timedelta(days=14), "form")
        a["final_status"] = "abandoned"
        continue
    ev(i, "form_submitted", t)

    # 2. Документы: паспорт (2 страницы) + «свидетельство ОГРНИП»
    abandon_p = 0.42 if device == "mobile" else 0.18
    abandon = rnd.random() < abandon_p
    err_p = 0.85 if abandon else (0.35 if device == "mobile" else 0.15)
    n_err = 0
    while rnd.random() < err_p and n_err < 4:
        n_err += 1
        reason = pick({"file_too_large": 45, "blurry_photo": 25, "no_ogrnip_certificate": 30} if device == "mobile"
                      else {"file_too_large": 15, "blurry_photo": 20, "no_ogrnip_certificate": 65})
        t += timedelta(minutes=lognorm(3, 0.5))
        ev(i, "upload_error", t, reason)
        err_p *= 0.6
    if abandon:
        ev(i, "abandoned", t + timedelta(days=14), "documents")
        a["final_status"] = "abandoned"
        continue
    t += timedelta(minutes=lognorm(4, 0.5))
    ev(i, "docs_uploaded", t)

    # 3. Автоматические проверки и маршрут
    t += timedelta(minutes=rnd.uniform(1, 6))
    route = as_is_route(a)
    a["route_as_is"] = route
    ev(i, "checks_done", t, route)
    if route == "refuse":
        ev(i, "refused", t + timedelta(minutes=2), "auto")
        a["final_status"] = "refused"
        continue

    # 4. Ручная проверка комплаенса (очередь, рабочие часы)
    if route == "manual":
        wait = lognorm(7, 0.8)
        t = work_hours_later(t, wait)
        ev(i, "review_started", t)
        t += timedelta(minutes=lognorm(22, 0.4))
        if is_risky and rnd.random() < 0.70:
            outcome = "refused"
        elif real_mismatch or (form_mismatch and rnd.random() < 0.55):
            outcome = "info_requested"
        else:
            outcome = "approved"
        ev(i, "review_done", t, outcome)
        if outcome == "refused":
            ev(i, "refused", t + timedelta(minutes=5), "manual")
            a["final_status"] = "refused"
            continue
        if outcome == "info_requested":
            if rnd.random() < 0.27:
                ev(i, "abandoned", t + timedelta(days=14), "info_request")
                a["final_status"] = "abandoned"
                continue
            t += timedelta(hours=lognorm(20, 0.7))
            ev(i, "info_provided", t)
            t = work_hours_later(t, lognorm(4, 0.6))
            t += timedelta(minutes=lognorm(10, 0.4))
            ev(i, "review_done", t, "approved")

    # 5. Идентификация: ЕБС (если есть биометрия) или встреча с представителем банка
    if has_ebs and rnd.random() < 0.6:
        t += timedelta(minutes=lognorm(25, 0.8))
        ev(i, "identified", t, "ebs")
    else:
        meet = (t + timedelta(days=rnd.choice([1, 1, 2, 2, 3, 4]))).replace(hour=rnd.randint(10, 19), minute=rnd.choice([0, 30]))
        if rnd.random() < 0.09:
            ev(i, "abandoned", meet + timedelta(days=14), "meeting")
            a["final_status"] = "abandoned"
            continue
        t = meet
        ev(i, "identified", t, "meeting")

    # 6. Открытие счёта (сообщение в ФНС — отдельный процесс, в данные не входит)
    t += timedelta(minutes=lognorm(15, 0.5))
    ev(i, "account_opened", t)
    a["final_status"] = "opened"

with open(OUT / "applications.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(apps[0].keys()))
    w.writeheader()
    for a in apps:
        w.writerow({k: (str(v).lower() if isinstance(v, bool) else v) for k, v in a.items()})
events.sort(key=lambda e: (e["event_at"], e["event_id"]))
with open(OUT / "app_events.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(events[0].keys()))
    w.writeheader()
    w.writerows(events)

opened = sum(a["final_status"] == "opened" for a in apps)
print(f"Заявок: {len(apps)}, событий: {len(events)}, счетов открыто: {opened} ({opened / len(apps):.1%})")
