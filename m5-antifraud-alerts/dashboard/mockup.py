"""Макет дашборда «Антифрод: процесс разбора алертов» (PNG) — как он будет выглядеть в DataLens.
Запуск: python dashboard/mockup.py  (нужен matplotlib; данные — dashboard/*.csv из export.sql)
Это не DataLens, а эскиз для README: настоящий дашборд собирается по инструкции docs/dashboard.md.
"""
import csv
from collections import defaultdict
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

D = Path(__file__).parent
SURF, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
SERIES = {"auto_block": "#2a78d6", "sms_confirm": "#eb6834", "analyst": "#1baf7a", "monitor": "#eda100"}
LABEL = {"auto_block": "Автоблок", "sms_confirm": "Подтверждение клиентом", "analyst": "Аналитик", "monitor": "Мониторинг"}

daily = defaultdict(dict)
tot = defaultdict(int)
for r in csv.DictReader(open(D / "daily_metrics.csv", encoding="utf-8")):
    daily[r["day"]][r["route"]] = int(r["alerts"])
    for k in ("alerts", "confirmed_fraud", "false_positives", "analyst_alerts"):
        tot[k] += int(r[k])
rules = list(csv.DictReader(open(D / "rule_hits.csv", encoding="utf-8")))
days = sorted(daily)

plt.rcParams.update({"font.family": "DejaVu Sans", "text.color": INK, "axes.labelcolor": INK2,
                     "xtick.color": INK2, "ytick.color": INK2, "axes.edgecolor": GRID})
fig = plt.figure(figsize=(14, 8.2), facecolor=SURF)
fig.text(0.04, 0.95, "Антифрод: разбор алертов, сентябрь 2026 (TO-BE, синтетические данные)", fontsize=16, weight="bold")

kpis = [("Алертов в день", f"{tot['alerts'] / len(days):.1f}"),
        ("Подтверждённое мошенничество", f"{100 * tot['confirmed_fraud'] / tot['alerts']:.1f} %"),
        ("Ложные срабатывания", f"{100 * tot['false_positives'] / tot['alerts']:.1f} %"),
        ("Алертов аналитику в день", f"{tot['analyst_alerts'] / len(days):.1f}")]
for i, (name, val) in enumerate(kpis):
    x = 0.04 + i * 0.235
    fig.patches.append(matplotlib.patches.FancyBboxPatch((x, 0.78), 0.215, 0.12, boxstyle="round,pad=0,rounding_size=0.01",
                       transform=fig.transFigure, facecolor="#ffffff", edgecolor=GRID))
    fig.text(x + 0.012, 0.865, name, fontsize=10.5, color=INK2)
    fig.text(x + 0.012, 0.80, val, fontsize=24, weight="bold")

ax = fig.add_axes([0.05, 0.1, 0.5, 0.58], facecolor=SURF)
bottom = [0] * len(days)
for route in ["auto_block", "sms_confirm", "analyst", "monitor"]:
    vals = [daily[d].get(route, 0) for d in days]
    ax.bar(range(len(days)), vals, bottom=bottom, color=SERIES[route], width=0.72, label=LABEL[route],
           edgecolor=SURF, linewidth=1.5)
    bottom = [b + v for b, v in zip(bottom, vals)]
ax.set_title("Алерты по дням и маршрутам", loc="left", fontsize=12, color=INK, pad=10)
ax.set_xticks(range(0, len(days), 5), [".".join(days[i].split("-")[::-1][:2]) for i in range(0, len(days), 5)])
ax.yaxis.grid(True, color=GRID, linewidth=0.8); ax.set_axisbelow(True)
for s in ("top", "right", "left"):
    ax.spines[s].set_visible(False)
ax.legend(loc="upper left", bbox_to_anchor=(0, -0.07), ncol=4, frameon=False, fontsize=9.5)

ax2 = fig.add_axes([0.775, 0.1, 0.2, 0.58], facecolor=SURF)
names = [f"{r['rule_code']}. {r['name']}" for r in rules][::-1]
prec = [100 * int(r["fraud_hits"]) / int(r["alerts"]) if int(r["alerts"]) else 0 for r in rules][::-1]
ax2.barh(names, prec, color="#2a78d6", height=0.55)
for y, p in enumerate(prec):
    ax2.text(p + 2, y, f"{p:.0f} %", va="center", fontsize=9.5, color=INK2)
ax2.set_xlim(0, 115)
ax2.set_title("Точность правил: доля\nподтверждённых алертов", loc="left", fontsize=12, color=INK, pad=10)
ax2.xaxis.set_visible(False)
for s in ("top", "right", "bottom"):
    ax2.spines[s].set_visible(False)
ax2.tick_params(axis="y", labelsize=9.5, length=0)

fig.savefig(D / "dashboard-mockup.png", dpi=110, facecolor=SURF)
print("ok", D / "dashboard-mockup.png")
