"""Сравнение маршрутизации AS-IS и TO-BE на тех же заявках.
AS-IS — правило, которое работает сейчас (см. docs/requirements.md). TO-BE — таблица решений bpmn/kyc-check-level.dmn
плюс автозаполнение анкеты из ЕГРИП: «ложные» расхождения из-за ручного ввода исчезают, остаются только настоящие.
TO-BE strict — тот же DMN, но правило KYC-09 выключено: новые ИП без группы ЗСК идут на ручную проверку, как сейчас.
Запуск из корня репозитория (после data/generate_data.py):  python tools/route_compare.py
"""
import csv
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from dmn_eval import evaluate  # noqa: E402

DMN = ROOT / "bpmn" / "kyc-check-level.dmn"
REVIEW_MIN = 422 * 60 / 1067  # средние минуты на проверку: 422 ч на 1 067 проверок (sql/03, раздел 3.5)
CATCH_RATE_FALLBACK = 0.8  # если в данных нет ручных проверок рискованных заявок


def b(v):
    return v == "true"


def as_is(a):
    if b(a["in_lists"]) or not b(a["passport_valid"]) or a["egrip_status"] == "ceased" or a["zsk_group"] == "high":
        return "REFUSE"
    if b(a["form_mismatch"]) or b(a["okved_watch"]) or a["zsk_group"] in ("medium", "none"):
        return "MANUAL"
    return "AUTO"


def to_be(a):
    return evaluate(DMN, "checkLevel", dict(
        inLists=b(a["in_lists"]), passportValid=b(a["passport_valid"]), egripStatus=a["egrip_status"],
        zskGroup=a["zsk_group"], dataMismatch=b(a["real_mismatch"]), okvedWatch=b(a["okved_watch"])))


apps = [a for a in csv.DictReader(open(ROOT / "data" / "applications.csv", encoding="utf-8")) if a["route_as_is"]]
assert all(as_is(a) == a["route_as_is"].upper() for a in apps), "правило AS-IS разошлось с данными"

rows = []
for a in apps:
    t = to_be(a)
    rows.append(dict(asis=as_is(a), tobe=t["level"], strict="MANUAL" if t["rule"] == "KYC-09" else t["level"], rule=t["rule"], post=t["postControl"], risky=b(a["is_risky"]),
                     refused_manual=a["final_status"] == "refused" and a["route_as_is"] == "manual"))

n = len(rows)
# качество ручной проверки берём из факта AS-IS: какую долю рискованных заявок комплаенс остановил
risky_manual = [r for r in rows if r["asis"] == "MANUAL" and r["risky"]]
catch = (sum(r["refused_manual"] for r in risky_manual) / len(risky_manual)) if risky_manual else CATCH_RATE_FALLBACK


def summary(key):
    c = Counter(r[key] for r in rows)
    manual = c["MANUAL"]
    risky_auto = sum(r[key] == "AUTO" and r["risky"] for r in rows)
    risky_manual_n = sum(r[key] == "MANUAL" and r["risky"] for r in rows)
    return dict(auto=c["AUTO"], manual=manual, refuse=c["REFUSE"], manual_pct=100 * manual / n,
                hours=manual * REVIEW_MIN / 60, risky_auto=risky_auto,
                risky_passed=risky_auto + risky_manual_n * (1 - catch))


s_as, s_st, s_to = summary("asis"), summary("strict"), summary("tobe")
print(f"Заявок, дошедших до проверок: {n}. Доля рискованных, которую ручная проверка останавливает (факт AS-IS): {catch:.0%}\n")
print(f"{'':38}{'AS-IS':>10}{'strict':>10}{'TO-BE':>10}")
for label, k, fmt in [("Авто", "auto", "{:.0f}"), ("Ручная проверка", "manual", "{:.0f}"),
                      ("Отказ без ручной проверки", "refuse", "{:.0f}"), ("Доля ручных, %", "manual_pct", "{:.1f}"),
                      ("Часы комплаенса за 3 месяца", "hours", "{:.0f}"),
                      ("Рискованных ушло в авто", "risky_auto", "{:.0f}"),
                      ("Рискованных получат счёт (оценка)", "risky_passed", "{:.1f}")]:
    print(f"{label:38}{fmt.format(s_as[k]):>10}{fmt.format(s_st[k]):>10}{fmt.format(s_to[k]):>10}")

post = [r for r in rows if r["post"]]
print(f"\nАвто с постконтролем (KYC-09): {len(post)} заявок, из них рискованных {sum(r['risky'] for r in post)} — "
      f"их ловит мониторинг операций первые 30 дней (лимиты, усиленный контроль).")
print("\nКуда ушли заявки (AS-IS → TO-BE):")
for (a, t), k in sorted(Counter((r["asis"], r["tobe"]) for r in rows).items()):
    print(f"  {a:7} → {t:7} {k:5}")
print("\nTO-BE по правилам:")
for rule, k in sorted(Counter(r["rule"] for r in rows).items()):
    print(f"  {rule}  {k:5}  ({100 * k / n:.1f} %)")
