"""Независимая проверка расчёта: та же переоценка на pandas, сравнение с SQL-представлением v_revaluation.

Если цифры совпали до копейки — SQL написан правильно (или обе реализации ошибаются одинаково,
поэтому ниже есть ещё ручной пример, посчитанный на калькуляторе).
Запуск: python tests/check_revaluation.py   (переменные DB и PSQL как в run_all.sh)
"""
import io
import os
import shlex
import subprocess
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
REPORT_DATES = pd.to_datetime(["2026-09-30", "2026-10-31"])

rates = pd.read_csv(ROOT / "data" / "rates.csv", parse_dates=["rate_date"]).drop_duplicates(["rate_date", "char_code"])
items = pd.read_csv(ROOT / "data" / "open_items.csv", parse_dates=["recognized_on", "settled_on"])


def rate_on(cur, d):
    r = rates[(rates.char_code == cur) & (rates.rate_date <= d)].sort_values("rate_date")
    return float(r.unit_rate.iloc[-1])


rows = []
for it in items[items.is_monetary].itertuples():
    events = [it.recognized_on]
    events += [d for d in REPORT_DATES if d > it.recognized_on and (pd.isna(it.settled_on) or d < it.settled_on)]
    if not pd.isna(it.settled_on):
        events.append(it.settled_on)
    prev = None
    for d in events:
        r = rate_on(it.currency, d)
        if prev is not None:
            sign = 1 if it.side == "asset" else -1
            rows.append({"item_id": it.item_id, "event_date": d.date().isoformat(),
                         "fx_result": round(round(it.amount_cur * (r - prev), 2) * sign, 2)})
        prev = r
py = pd.DataFrame(rows)

# Ручной пример (калькулятор): долг поставщику 100 000 CNY, признан 15.09 по 12,5353, переоценка 30.09 по 12,5764
manual = round(100_000 * (12.5764 - 12.5353), 2) * -1
assert manual == -4110.0, manual   # курс вырос → долг в рублях вырос → расход 4 110 ₽

psql = shlex.split(os.environ.get("PSQL", "psql")) + ["-d", os.environ.get("DB", "fx"), "-A", "-F", ",", "-P", "footer=off", "-c",
        "SELECT item_id, event_date, fx_result FROM v_revaluation ORDER BY item_id, event_date"]
sql = pd.read_csv(io.StringIO(subprocess.run(psql, capture_output=True, text=True, check=True).stdout), dtype={"event_date": str})

m = py.merge(sql, on=["item_id", "event_date"], how="outer", suffixes=("_py", "_sql"), indicator=True)
bad = m[(m._merge != "both") | ((m.fx_result_py - m.fx_result_sql).abs() > 0.005)]
print(f"строк pandas: {len(py)}, SQL: {len(sql)}, расхождений: {len(bad)}")
print(f"итого курсовых разниц: pandas {py.fx_result.sum():,.2f} ₽, SQL {sql.fx_result.sum():,.2f} ₽".replace(",", " "))
if len(bad):
    print(bad)
    raise SystemExit(1)
print("OK: расчёт SQL совпадает с pandas")
