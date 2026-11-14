"""Собирает model/cash_flow_budget.xlsx — БДДС план-факт и платёжный календарь ООО «Ромашка-Опт» (вымышленная).
Запуск:  pip install openpyxl  →  python model/build_model.py
Все расчёты в книге — живые формулы Excel (SUMIFS, INDEX/MATCH, MIN, COUNTIF...). Python только кладёт
исходные данные (справочники, план, фактические операции, план платежей) и формулы. random.seed фиксирован.

Что заложено в данные: поступления от покупателей отстают от плана всё сильнее (растёт DSO, см. проект M4); покупатели платят
каждый рабочий день, поставщикам платим по вторникам и четвергам;
закупки чуть выше плана, в ноябре покупка погрузчика, налоги по ЕНП 28-го числа, зарплата 10-го и 25-го.
"""
import random
from datetime import date, timedelta
from pathlib import Path

from openpyxl import Workbook
from openpyxl.formatting.rule import CellIsRule, FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter as L
from openpyxl.worksheet.datavalidation import DataValidation

random.seed(7)
OUT = Path(__file__).parent / "cash_flow_budget.xlsx"

CFO = ["Продажи", "Закупки", "Склад", "Логистика", "Администрация", "Финансы"]
# код, статья, направление, вид деятельности
ITEMS = [
    ("П01", "Поступления от покупателей", "Поступление", "Операционная"),
    ("П02", "Прочие поступления", "Поступление", "Операционная"),
    ("П03", "Получение кредитов и овердрафта", "Поступление", "Финансовая"),
    ("В01", "Оплата поставщикам товара", "Выбытие", "Операционная"),
    ("В02", "Зарплата", "Выбытие", "Операционная"),
    ("В03", "Налоги и взносы (ЕНП)", "Выбытие", "Операционная"),
    ("В04", "Аренда склада и офиса", "Выбытие", "Операционная"),
    ("В05", "Логистика и доставка", "Выбытие", "Операционная"),
    ("В06", "ИТ и связь", "Выбытие", "Операционная"),
    ("В07", "Маркетинг", "Выбытие", "Операционная"),
    ("В08", "Покупка оборудования", "Выбытие", "Инвестиционная"),
    ("В09", "Погашение кредита", "Выбытие", "Финансовая"),
    ("В10", "Проценты по кредиту", "Выбытие", "Финансовая"),
]
MONTHS = [date(2026, m, 1) for m in range(7, 13)]      # июль–декабрь
FACT_MONTHS = MONTHS[:4]                                # факт есть по октябрь
OPENING = 1_800_000                                     # остаток на 01.07.2026
RESERVE = 2_000_000                                     # неснижаемый остаток (политика компании)
SALARY = {"Продажи": 900_000, "Закупки": 250_000, "Склад": 700_000, "Логистика": 450_000,
          "Администрация": 500_000, "Финансы": 300_000}


def plan_v1(month):
    """Бюджет v1, утверждён в июне: строки (ЦФО, код, сумма) на месяц."""
    k = 1 + 0.01 * (month.month - 7)                    # план роста продаж 1 % в месяц
    rows = [("Продажи", "П01", 22_000_000 * k * (1.12 if month.month == 12 else 1)),
            ("Финансы", "П02", 150_000),
            ("Закупки", "В01", 13_600_000 * k * (1.06 if month.month == 12 else 1)),
            ("Финансы", "В03", 1_900_000),
            ("Администрация", "В04", 650_000), ("Логистика", "В05", 950_000),
            ("Администрация", "В06", 220_000), ("Продажи", "В07", 300_000),
            ("Финансы", "В09", 500_000), ("Финансы", "В10", 120_000 - 5_000 * (month.month - 7))]
    rows += [(c, "В02", s) for c, s in SALARY.items()]
    if month.month == 11:
        rows.append(("Склад", "В08", 2_600_000))         # погрузчик
    return [(c, code, round(a, -3)) for c, code, a in rows]


# Фактические отклонения от плана по месяцам (доля): поступления отстают всё сильнее — растёт DSO
DEV = {"П01": [-0.005, -0.01, -0.02, -0.035], "В01": [0.005, 0.01, 0.015, 0.02], "В05": [0, 0.03, 0.06, 0.15],
       "В07": [-0.2, -0.1, -0.25, -0.15]}
DAY_RULES = {"В02": [10, 25], "В03": [28], "В04": [5], "В09": [15], "В10": [15], "П02": [20]}
PARTNERS = {"П01": ["ООО «Сеть Клён»", "ООО «Продукты Орбита»", "ИП Ткач М. Е.", "ООО «Сеть Калина»", "ООО «Гастроном Горница»"],
            "В01": ["ООО «Бакалея-Опт»", "АО «Молочный двор»", "ООО «Консервы Юг»", "ООО «Напитки Плюс»"],
            "В05": ["ООО «ЛогистПлюс»"], "В04": ["АО «Склад-Парк»"], "В06": ["ООО «Связь-Онлайн»"],
            "В07": ["ООО «Реклама 360»"], "В02": ["Сотрудники"], "В03": ["ФНС (ЕНП)"], "В08": ["ООО «ТехноСклад»"],
            "В09": ["Банк «Пример»"], "В10": ["Банк «Пример»"], "П02": ["Банк «Пример»"]}


def workday(d):
    """Срок на выходной переносится на следующий рабочий день (как налоги по ЕНП)."""
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


def split(code, cfo, month, total, ops_n):
    """Разбить сумму на операции с датами по правилам статьи."""
    last = (month.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    if code in ("П01", "В01"):
        # покупатели платят каждый рабочий день, поставщикам платим по вторникам и четвергам
        allowed = {0, 1, 2, 3, 4} if code == "П01" else {1, 3}
        dates = [month + timedelta(days=i) for i in range(last.day) if (month + timedelta(days=i)).weekday() in allowed]
        w = [random.uniform(0.8, 1.2) for _ in dates]
        parts = [total * x / sum(w) for x in w]
    elif code in DAY_RULES:
        days = DAY_RULES[code]
        parts = [total / len(days)] * len(days)
        dates = [workday(month.replace(day=min(dd, last.day))) for dd in days]
    else:
        w = [random.uniform(0.6, 1.4) for _ in range(ops_n)]
        parts = [total * x / sum(w) for x in w]
        dates = [workday(month + timedelta(days=random.randrange(last.day))) for _ in range(ops_n)]
    out = []
    for dt, p in zip(dates, parts):
        if dt > last:                      # перенос с выходных не должен уводить в следующий месяц
            dt = last - timedelta(days=(last.weekday() - 4) if last.weekday() > 4 else 0)
        out.append((dt, cfo, code, round(p, 2), random.choice(PARTNERS.get(code, ["—"]))))
    return out


OPS_N = {"В05": 4, "В06": 2, "В07": 2, "В08": 1}
fact = []
for i, m in enumerate(FACT_MONTHS):
    for cfo, code, amt in plan_v1(m):
        dev = DEV.get(code, [random.uniform(-0.02, 0.02)] * 4)[i]
        fact += split(code, cfo, m, amt * (1 + dev), OPS_N.get(code, 1))
fact.sort()

# Прогноз v2 (ноябрь) = план платежей с датами на ноябрь–декабрь. Из него строятся и БДДС-прогноз, и календарь.
FORECAST_DEV = {"П01": -0.03, "В01": 0.02, "В05": 0.12, "В07": -0.15}
payments = []
for m in MONTHS[4:]:
    for cfo, code, amt in plan_v1(m):
        dev = FORECAST_DEV.get(code, 0)
        if code == "В08":   # погрузчик подорожал до 4 млн, поставщик просит 50 % предоплаты и 50 % при поставке
            payments.append((date(2026, 11, 26), cfo, code, 2_000_000, "ООО «ТехноСклад»"))
            payments.append((date(2026, 12, 8), cfo, code, 2_000_000, "ООО «ТехноСклад»"))
            continue
        payments += split(code, cfo, m, amt * (1 + dev), OPS_N.get(code, 1))
payments.sort()
PRIORITY = {"В02": 1, "В03": 1, "В09": 1, "В10": 1, "В01": 2, "В04": 2, "В05": 2, "В06": 2, "В07": 3, "В08": 3}

# ---------------------------------------------------------------- книга Excel
wb = Workbook()
H = Font(bold=True, color="FFFFFF")
HF = PatternFill("solid", fgColor="305496")
INP = PatternFill("solid", fgColor="FFF2CC")        # жёлтые ячейки — исходные данные и допущения
TOT = PatternFill("solid", fgColor="D9E1F2")
B = Font(bold=True)
MONEY = '#,##0;[Red]-#,##0'
thin = Side(style="thin", color="BFBFBF")


def header(ws, row, values, col=1):
    for j, v in enumerate(values):
        c = ws.cell(row=row, column=col + j, value=v)
        c.font, c.fill, c.alignment = H, HF, Alignment(horizontal="center", vertical="center", wrap_text=True)


def widths(ws, w):
    for i, x in enumerate(w, 1):
        ws.column_dimensions[L(i)].width = x


# 0. Инструкция
ws = wb.active
ws.title = "Инструкция"
lines = [
    ("БДДС и платёжный календарь ООО «Ромашка-Опт» (учебная модель, данные синтетические)", B),
    ("", None),
    ("Как устроена книга", B),
    ("Справочники — ЦФО, статьи БДДС (направление, вид деятельности), версии бюджета, параметры.", None),
    ("План — бюджет v1 (утверждён в июне) в виде длинной таблицы: версия × месяц × ЦФО × статья.", None),
    ("Факт_операции — операции по расчётному счёту за июль–октябрь (в жизни — выгрузка из 1С или выписки).", None),
    ("Платежи_план — прогноз v2 на ноябрь–декабрь: каждый ожидаемый платёж с датой и приоритетом.", None),
    ("План_факт — июль–октябрь: план, факт, отклонение и % по каждой статье. Красным — отклонения больше 5 %.", None),
    ("БДДС_прогноз — июль–декабрь: факт по октябрь + прогноз v2, остаток на конец месяца, потоки по видам деятельности.", None),
    ("Платёжный_календарь — ноябрь–декабрь по неделям: где остаток уходит ниже нуля (кассовый разрыв) или ниже резерва.", None),
    ("Сценарии — как закрыть разрыв: овердрафт или перенос платежей приоритета 3; что делать с излишком.", None),
    ("Сводная_ЦФО — выбытия по ЦФО и месяцам (на формулах; задание: построить настоящую сводную таблицу).", None),
    ("", None),
    ("Правила", B),
    ("Жёлтые ячейки — вводимые данные и допущения, всё остальное считается формулами. Суммы в рублях, выбытия — положительными числами.", None),
    ("Чтобы добавить операцию: новая строка в Факт_операции или Платежи_план, серые колонки протяните формулой вниз.", None),
]
for i, (t, f) in enumerate(lines, 1):
    c = ws.cell(row=i, column=1, value=t)
    if f:
        c.font = f
ws.column_dimensions["A"].width = 130

# 1. Справочники
ws = wb.create_sheet("Справочники")
header(ws, 1, ["ЦФО"])
for i, c in enumerate(CFO, 2):
    ws.cell(row=i, column=1, value=c).fill = INP
header(ws, 1, ["Код", "Статья БДДС", "Направление", "Вид деятельности"], col=3)
for i, it in enumerate(ITEMS, 2):
    for j, v in enumerate(it):
        ws.cell(row=i, column=3 + j, value=v).fill = INP
ITEM_RANGE = f"Справочники!$C$2:$C${len(ITEMS) + 1}"
header(ws, 1, ["Версия", "Когда и зачем"], col=8)
ws["H2"], ws["I2"] = "Бюджет v1", "Утверждён генеральным директором в июне 2026"
ws["H3"], ws["I3"] = "Прогноз v2", "Переоценка в ноябре: факт по октябрь + новый план платежей на ноябрь–декабрь"
header(ws, 5, ["Параметр", "Значение"], col=8)
params = [("Остаток на 01.07.2026, ₽", OPENING), ("Неснижаемый остаток (резерв), ₽", RESERVE),
          ("Ставка овердрафта, % годовых (допущение)", 0.22),
          ("Ставка депозита, % годовых (допущение: проверьте ключевую ставку на cbr.ru)", 0.14),
          ("Порог отклонения для подсветки", 0.05)]
for i, (k, v) in enumerate(params, 6):
    ws.cell(row=i, column=8, value=k)
    c = ws.cell(row=i, column=9, value=v)
    c.fill = INP
    c.number_format = "0%" if v < 1 else MONEY
P_OPEN, P_RES, P_OVD, P_DEP, P_THR = "Справочники!$I$6", "Справочники!$I$7", "Справочники!$I$8", "Справочники!$I$9", "Справочники!$I$10"
widths(ws, [16, 3, 7, 34, 14, 16, 3, 70, 16])

# 2. План (длинная таблица)
ws = wb.create_sheet("План")
header(ws, 1, ["Версия", "Месяц", "ЦФО", "Код", "Статья", "Сумма"])
r = 2
for m in MONTHS:
    for cfo, code, amt in plan_v1(m):
        ws.cell(row=r, column=1, value="Бюджет v1").fill = INP
        ws.cell(row=r, column=2, value=m).number_format = "mmm yyyy"
        ws.cell(row=r, column=3, value=cfo).fill = INP
        ws.cell(row=r, column=4, value=code).fill = INP
        ws.cell(row=r, column=5, value=f"=INDEX(Справочники!$D:$D,MATCH(D{r},Справочники!$C:$C,0))")
        c = ws.cell(row=r, column=6, value=amt)
        c.fill, c.number_format = INP, MONEY
        r += 1
PLAN_LAST = r - 1
widths(ws, [12, 11, 15, 7, 32, 14])
ws.freeze_panes = "A2"

# 3. Факт_операции
ws = wb.create_sheet("Факт_операции")
header(ws, 1, ["Дата", "ЦФО", "Код", "Статья", "Направление", "Сумма", "Вид деятельности", "Месяц", "Контрагент"])
for i, (dt, cfo, code, amt, partner) in enumerate(fact, 2):
    ws.cell(row=i, column=1, value=dt).number_format = "dd.mm.yyyy"
    ws.cell(row=i, column=2, value=cfo)
    ws.cell(row=i, column=3, value=code)
    ws.cell(row=i, column=4, value=f"=INDEX(Справочники!$D:$D,MATCH(C{i},Справочники!$C:$C,0))")
    ws.cell(row=i, column=5, value=f"=INDEX(Справочники!$E:$E,MATCH(C{i},Справочники!$C:$C,0))")
    ws.cell(row=i, column=6, value=amt).number_format = MONEY
    ws.cell(row=i, column=7, value=f"=INDEX(Справочники!$F:$F,MATCH(C{i},Справочники!$C:$C,0))")
    ws.cell(row=i, column=8, value=f"=DATE(YEAR(A{i}),MONTH(A{i}),1)").number_format = "mmm yyyy"
    ws.cell(row=i, column=9, value=partner)
FACT_LAST = len(fact) + 1
widths(ws, [11, 15, 7, 32, 13, 14, 15, 11, 26])
ws.freeze_panes = "A2"
ws.auto_filter.ref = f"A1:I{FACT_LAST}"
dv = DataValidation(type="list", formula1=ITEM_RANGE, allow_blank=False)
ws.add_data_validation(dv)
dv.add(f"C2:C{FACT_LAST + 200}")

# 4. Платежи_план (прогноз v2)
ws = wb.create_sheet("Платежи_план")
header(ws, 1, ["Дата", "ЦФО", "Код", "Статья", "Направление", "Сумма", "Вид деятельности", "Месяц",
               "Неделя (пн)", "Контрагент", "Приоритет"])
for i, (dt, cfo, code, amt, partner) in enumerate(payments, 2):
    ws.cell(row=i, column=1, value=dt).number_format = "dd.mm.yyyy"
    ws.cell(row=i, column=2, value=cfo).fill = INP
    ws.cell(row=i, column=3, value=code).fill = INP
    ws.cell(row=i, column=4, value=f"=INDEX(Справочники!$D:$D,MATCH(C{i},Справочники!$C:$C,0))")
    ws.cell(row=i, column=5, value=f"=INDEX(Справочники!$E:$E,MATCH(C{i},Справочники!$C:$C,0))")
    c = ws.cell(row=i, column=6, value=amt)
    c.number_format, c.fill = MONEY, INP
    ws.cell(row=i, column=7, value=f"=INDEX(Справочники!$F:$F,MATCH(C{i},Справочники!$C:$C,0))")
    ws.cell(row=i, column=8, value=f"=DATE(YEAR(A{i}),MONTH(A{i}),1)").number_format = "mmm yyyy"
    ws.cell(row=i, column=9, value=f"=A{i}-WEEKDAY(A{i},2)+1").number_format = "dd.mm"
    ws.cell(row=i, column=10, value=partner)
    pr = PRIORITY.get(code)
    ws.cell(row=i, column=11, value=pr if pr else "—").fill = INP
    ws.cell(row=i, column=1).fill = INP
PAY_LAST = len(payments) + 1
widths(ws, [11, 15, 7, 32, 13, 14, 15, 11, 11, 26, 10])
ws.freeze_panes = "A2"
ws.auto_filter.ref = f"A1:K{PAY_LAST}"
ws.cell(row=PAY_LAST + 2, column=1, value="Приоритет: 1 — обязательные (налоги, зарплата, кредит), 2 — по договору, 3 — можно перенести").font = Font(italic=True)

F = lambda col: f"Факт_операции!${col}$2:${col}${FACT_LAST}"
PP = lambda col: f"Платежи_план!${col}$2:${col}${PAY_LAST}"
PL = lambda col: f"План!${col}$2:${col}${PLAN_LAST}"

# 5. План_факт (июль–октябрь)
ws = wb.create_sheet("План_факт")
ws["A1"] = "План-факт БДДС, июль–октябрь 2026 (бюджет v1)"
ws["A1"].font = Font(bold=True, size=13)
header(ws, 3, ["Код", "Статья", "Направление"])
ws.merge_cells("A3:A4"); ws.merge_cells("B3:B4"); ws.merge_cells("C3:C4")
cols = FACT_MONTHS + ["Итого"]
for k, m in enumerate(cols):
    c0 = 4 + k * 4
    ws.merge_cells(start_row=3, start_column=c0, end_row=3, end_column=c0 + 3)
    cell = ws.cell(row=3, column=c0, value=m)
    cell.number_format = "mmmm yyyy"
    header(ws, 4, ["План", "Факт", "Откл.", "Откл. %"], col=c0)
    cell.font, cell.fill, cell.alignment = H, HF, Alignment(horizontal="center")
first = 5
for i, (code, name, direction, _) in enumerate(ITEMS):
    r = first + i
    ws.cell(row=r, column=1, value=code)
    ws.cell(row=r, column=2, value=name)
    ws.cell(row=r, column=3, value=direction)
    for k, m in enumerate(FACT_MONTHS):
        c0 = 4 + k * 4
        mcell = f"{L(c0)}$3"
        ws.cell(row=r, column=c0, value=f'=SUMIFS({PL("F")},{PL("A")},"Бюджет v1",{PL("B")},{mcell},{PL("D")},$A{r})')
        ws.cell(row=r, column=c0 + 1, value=f'=SUMIFS({F("F")},{F("H")},{mcell},{F("C")},$A{r})')
    c0 = 4 + 4 * 4
    for off in (0, 1):
        ws.cell(row=r, column=c0 + off, value="=" + "+".join(f"{L(4 + k * 4 + off)}{r}" for k in range(4)))
    for k in range(5):
        c0 = 4 + k * 4
        ws.cell(row=r, column=c0 + 2, value=f"={L(c0 + 1)}{r}-{L(c0)}{r}")
        ws.cell(row=r, column=c0 + 3, value=f'=IF({L(c0)}{r}=0,"",{L(c0 + 2)}{r}/{L(c0)}{r})')
last_item = first + len(ITEMS) - 1
tot_rows = [("Итого поступления", "Поступление"), ("Итого выбытия", "Выбытие")]
for j, (label, d) in enumerate(tot_rows):
    r = last_item + 1 + j
    ws.cell(row=r, column=2, value=label).font = B
    for k in range(5):
        c0 = 4 + k * 4
        for off in (0, 1):
            col = L(c0 + off)
            ws.cell(row=r, column=c0 + off, value=f'=SUMIFS({col}{first}:{col}{last_item},$C${first}:$C${last_item},"{d}")')
        ws.cell(row=r, column=c0 + 2, value=f"={L(c0 + 1)}{r}-{L(c0)}{r}")
        ws.cell(row=r, column=c0 + 3, value=f'=IF({L(c0)}{r}=0,"",{L(c0 + 2)}{r}/{L(c0)}{r})')
r_in, r_out = last_item + 1, last_item + 2
r_net = last_item + 3
ws.cell(row=r_net, column=2, value="Чистый денежный поток").font = B
for k in range(5):
    c0 = 4 + k * 4
    for off in (0, 1):
        col = L(c0 + off)
        ws.cell(row=r_net, column=c0 + off, value=f"={col}{r_in}-{col}{r_out}")
    ws.cell(row=r_net, column=c0 + 2, value=f"={L(c0 + 1)}{r_net}-{L(c0)}{r_net}")
for rr in range(first, r_net + 1):
    for cc in range(4, 24):
        cell = ws.cell(row=rr, column=cc)
        cell.number_format = "0.0%" if (cc - 4) % 4 == 3 else MONEY
        if rr > last_item:
            cell.fill = TOT
            cell.font = B
red = PatternFill("solid", fgColor="F8CBAD")
for k in range(5):
    pc = L(4 + k * 4 + 3)
    ws.conditional_formatting.add(f"{pc}{first}:{pc}{r_net}",
                                  FormulaRule(formula=[f'AND(ISNUMBER({pc}{first}),ABS({pc}{first})>{P_THR})'], fill=red))
widths(ws, [6, 32, 12] + [13, 13, 12, 8] * 5)
ws.freeze_panes = "D5"

# 6. БДДС_прогноз (июль–декабрь: факт + прогноз v2)
ws = wb.create_sheet("БДДС_прогноз")
ws["A1"] = "БДДС 2026, II полугодие: факт (июль–октябрь) + прогноз v2 (ноябрь–декабрь)"
ws["A1"].font = Font(bold=True, size=13)
header(ws, 3, ["Код", "Статья", "Направление", "Вид"] + [None] * 6 + ["Итого прогноз", "Бюджет v1", "Откл."])
for k, m in enumerate(MONTHS):
    c = ws.cell(row=3, column=5 + k, value=m)
    c.number_format = "mmm yyyy"
    c.font, c.fill = H, HF
for k, m in enumerate(MONTHS):
    ws.cell(row=4, column=5 + k, value="факт" if m in FACT_MONTHS else "прогноз v2").alignment = Alignment(horizontal="center")
first = 5
for i, (code, name, direction, act) in enumerate(ITEMS):
    r = first + i
    for j, v in enumerate((code, name, direction, act)):
        ws.cell(row=r, column=1 + j, value=v)
    for k, m in enumerate(MONTHS):
        mc = f"{L(5 + k)}$3"
        src = (f'SUMIFS({F("F")},{F("H")},{mc},{F("C")},$A{r})' if m in FACT_MONTHS
               else f'SUMIFS({PP("F")},{PP("H")},{mc},{PP("C")},$A{r})')
        ws.cell(row=r, column=5 + k, value="=" + src)
    ws.cell(row=r, column=11, value=f"=SUM(E{r}:J{r})")
    ws.cell(row=r, column=12, value=f'=SUMIFS({PL("F")},{PL("A")},"Бюджет v1",{PL("D")},$A{r})')
    ws.cell(row=r, column=13, value=f"=K{r}-L{r}")
last_item = first + len(ITEMS) - 1
labels = ["Остаток на начало месяца", "Итого поступления", "Итого выбытия", "Чистый поток: операционная",
          "Чистый поток: инвестиционная", "Чистый поток: финансовая", "Чистый денежный поток",
          "Остаток на конец месяца", "Неснижаемый остаток", "Статус"]
R = {lab: last_item + 2 + i for i, lab in enumerate(labels)}
rng = lambda col, a, b: f"{col}{a}:{col}{b}"
for lab, r in R.items():
    ws.cell(row=r, column=2, value=lab).font = B
for k in range(6):
    col = L(5 + k)
    prev = L(4 + k)
    ws[f"{col}{R['Остаток на начало месяца']}"] = f"={P_OPEN}" if k == 0 else f"={prev}{R['Остаток на конец месяца']}"
    ws[f"{col}{R['Итого поступления']}"] = f'=SUMIFS({rng(col, first, last_item)},$C${first}:$C${last_item},"Поступление")'
    ws[f"{col}{R['Итого выбытия']}"] = f'=SUMIFS({rng(col, first, last_item)},$C${first}:$C${last_item},"Выбытие")'
    for lab, act in (("Чистый поток: операционная", "Операционная"), ("Чистый поток: инвестиционная", "Инвестиционная"),
                     ("Чистый поток: финансовая", "Финансовая")):
        ws[f"{col}{R[lab]}"] = (f'=SUMIFS({rng(col, first, last_item)},$C${first}:$C${last_item},"Поступление",$D${first}:$D${last_item},"{act}")'
                                f'-SUMIFS({rng(col, first, last_item)},$C${first}:$C${last_item},"Выбытие",$D${first}:$D${last_item},"{act}")')
    ws[f"{col}{R['Чистый денежный поток']}"] = f"={col}{R['Итого поступления']}-{col}{R['Итого выбытия']}"
    ws[f"{col}{R['Остаток на конец месяца']}"] = f"={col}{R['Остаток на начало месяца']}+{col}{R['Чистый денежный поток']}"
    ws[f"{col}{R['Неснижаемый остаток']}"] = f"={P_RES}"
    ws[f"{col}{R['Статус']}"] = (f'=IF({col}{R["Остаток на конец месяца"]}<0,"РАЗРЫВ",'
                                 f'IF({col}{R["Остаток на конец месяца"]}<{col}{R["Неснижаемый остаток"]},"ниже резерва","ок"))')
for lab in ("Итого поступления", "Итого выбытия", "Чистый поток: операционная", "Чистый поток: инвестиционная",
            "Чистый поток: финансовая", "Чистый денежный поток"):
    ws[f"K{R[lab]}"] = f"=SUM(E{R[lab]}:J{R[lab]})"
for rr in range(first, R["Статус"]):
    for cc in range(5, 14):
        ws.cell(row=rr, column=cc).number_format = MONEY
for rr in range(R["Остаток на начало месяца"], R["Статус"] + 1):
    for cc in range(2, 14):
        ws.cell(row=rr, column=cc).fill = TOT
st = f"E{R['Статус']}:J{R['Статус']}"
ws.conditional_formatting.add(st, CellIsRule(operator="equal", formula=['"РАЗРЫВ"'], fill=PatternFill("solid", fgColor="FF7C80")))
ws.conditional_formatting.add(st, CellIsRule(operator="equal", formula=['"ниже резерва"'], fill=PatternFill("solid", fgColor="FFE699")))
widths(ws, [6, 32, 12, 14] + [13] * 6 + [14, 14, 13])
ws.freeze_panes = "E5"
BDDS_OCT_END = f"БДДС_прогноз!$H${R['Остаток на конец месяца']}"

# 7. Платёжный_календарь (ноябрь–декабрь по неделям)
ws = wb.create_sheet("Платёжный_календарь")
ws["A1"] = "Платёжный календарь, ноябрь–декабрь 2026 (прогноз v2), по неделям с понедельника"
ws["A1"].font = Font(bold=True, size=13)
weeks = [date(2026, 11, 2) + timedelta(weeks=i) for i in range(9)]
header(ws, 3, ["Строка"])
for k, wk in enumerate(weeks):
    c = ws.cell(row=3, column=2 + k, value=wk)
    c.number_format = "dd.mm"
    c.font, c.fill, c.alignment = H, HF, Alignment(horizontal="center")
rows = ["Остаток на начало недели", "Поступления", "Выбытия: приоритет 1 (налоги, зарплата, кредит)",
        "Выбытия: приоритет 2 (по договору)", "Выбытия: приоритет 3 (можно перенести)", "Итого выбытия",
        "Чистый поток", "Остаток на конец недели", "Неснижаемый остаток", "Статус"]
C = {lab: 4 + i for i, lab in enumerate(rows)}
for lab, r in C.items():
    ws.cell(row=r, column=1, value=lab).font = B
for k in range(len(weeks)):
    col, prev = L(2 + k), L(1 + k)
    wk = f"{col}$3"
    ws[f"{col}{C['Остаток на начало недели']}"] = f"={BDDS_OCT_END}" if k == 0 else f"={prev}{C['Остаток на конец недели']}"
    ws[f"{col}{C['Поступления']}"] = f'=SUMIFS({PP("F")},{PP("I")},{wk},{PP("E")},"Поступление")'
    for p, lab in ((1, "Выбытия: приоритет 1 (налоги, зарплата, кредит)"), (2, "Выбытия: приоритет 2 (по договору)"),
                   (3, "Выбытия: приоритет 3 (можно перенести)")):
        ws[f"{col}{C[lab]}"] = f'=SUMIFS({PP("F")},{PP("I")},{wk},{PP("E")},"Выбытие",{PP("K")},{p})'
    ws[f"{col}{C['Итого выбытия']}"] = f"=SUM({col}{C['Выбытия: приоритет 1 (налоги, зарплата, кредит)']}:{col}{C['Выбытия: приоритет 3 (можно перенести)']})"
    ws[f"{col}{C['Чистый поток']}"] = f"={col}{C['Поступления']}-{col}{C['Итого выбытия']}"
    ws[f"{col}{C['Остаток на конец недели']}"] = f"={col}{C['Остаток на начало недели']}+{col}{C['Чистый поток']}"
    ws[f"{col}{C['Неснижаемый остаток']}"] = f"={P_RES}"
    end, res = f"{col}{C['Остаток на конец недели']}", f"{col}{C['Неснижаемый остаток']}"
    ws[f"{col}{C['Статус']}"] = f'=IF({end}<0,"РАЗРЫВ",IF({end}<{res},"ниже резерва","ок"))'
lastc = L(1 + len(weeks))
for rr in range(4, C["Статус"]):
    for cc in range(2, 2 + len(weeks)):
        ws.cell(row=rr, column=cc).number_format = MONEY
ws.conditional_formatting.add(f"B{C['Статус']}:{lastc}{C['Статус']}", CellIsRule(operator="equal", formula=['"РАЗРЫВ"'], fill=PatternFill("solid", fgColor="FF7C80")))
ws.conditional_formatting.add(f"B{C['Статус']}:{lastc}{C['Статус']}", CellIsRule(operator="equal", formula=['"ниже резерва"'], fill=PatternFill("solid", fgColor="FFE699")))
ws.conditional_formatting.add(f"B{C['Остаток на конец недели']}:{lastc}{C['Остаток на конец недели']}",
                              CellIsRule(operator="lessThan", formula=["0"], fill=PatternFill("solid", fgColor="FF7C80")))
# Проверка: календарь сходится с БДДС_прогноз (ноябрь + декабрь, выбытия)
chk = C["Статус"] + 2
ws.cell(row=chk, column=1, value="Проверка: выбытия календаря = выбытия БДДС за ноябрь–декабрь").font = Font(italic=True)
ws.cell(row=chk, column=2, value=f"=SUM(B{C['Итого выбытия']}:{lastc}{C['Итого выбытия']})-SUM(БДДС_прогноз!I{R['Итого выбытия']}:J{R['Итого выбытия']})").number_format = MONEY
widths(ws, [46] + [13] * len(weeks))
ws.freeze_panes = "B4"
CAL_END = f"Платёжный_календарь!$B${C['Остаток на конец недели']}:${lastc}${C['Остаток на конец недели']}"
CAL_P3 = C["Выбытия: приоритет 3 (можно перенести)"]

# 8. Сценарии
ws = wb.create_sheet("Сценарии")
ws["A1"] = "Как закрыть кассовый разрыв и что делать с излишком"
ws["A1"].font = Font(bold=True, size=13)
items = [
    ("Минимальный остаток на конец недели, ₽", f"=MIN({CAL_END})"),
    ("Неделя минимума (понедельник)", f"=INDEX(Платёжный_календарь!$B$3:${lastc}$3,MATCH(B3,{CAL_END},0))"),
    ("Недель с разрывом (остаток < 0)", f'=COUNTIF({CAL_END},"<0")'),
    ("Недель ниже резерва", f'=COUNTIF({CAL_END},"<"&{P_RES})'),
    ("Размер разрыва, ₽", "=MAX(0,-B3)"),
    ("Сценарий А. Овердрафт на разрыв + резерв, ₽", f"=MAX(0,{P_RES}-B3)"),
    ("Стоимость овердрафта за 2 недели, ₽", f"=B8*{P_OVD}*14/365"),
    ("Сценарий Б. Остаток в неделю минимума, если платежи приоритета 3 перенести на 2 недели, ₽", "=B3+INDEX(Платёжный_календарь!$B${p3}:${lc}${p3},MATCH(B4,Платёжный_календарь!$B$3:${lc}$3,0))".format(p3=CAL_P3, lc=lastc)),
    ("Максимальный остаток на конец недели, ₽", f"=MAX({CAL_END})"),
    ("Излишек сверх резерва в эту неделю, ₽", f"=MAX(0,B11-{P_RES})"),
    ("Сценарий В. Доход, если излишек положить на депозит на 1 неделю, ₽", f"=B12*{P_DEP}*7/365"),
]
for i, (k, v) in enumerate(items, 3):
    ws.cell(row=i, column=1, value=k)
    c = ws.cell(row=i, column=2, value=v)
    c.number_format = "dd.mm.yyyy" if "понедельник" in k else (MONEY if "₽" in k else "0")
ws.cell(row=15, column=1, value="Сценарий Б упрощён: переносится вся сумма приоритета 3 недели минимума. Проверьте, нет ли в ней обязательных платежей.").font = Font(italic=True)
widths(ws, [92, 16])

# 9. Сводная_ЦФО
ws = wb.create_sheet("Сводная_ЦФО")
ws["A1"] = "Выбытия по ЦФО и месяцам, факт (на формулах SUMIFS). Задание CR-1: построить то же настоящей сводной таблицей."
ws["A1"].font = B
header(ws, 3, ["ЦФО"] + [None] * 4 + ["Итого"])
for k, m in enumerate(FACT_MONTHS):
    c = ws.cell(row=3, column=2 + k, value=m)
    c.number_format = "mmm yyyy"
    c.font, c.fill = H, HF
for i, cfo in enumerate(CFO, 4):
    ws.cell(row=i, column=1, value=cfo)
    for k in range(4):
        col = L(2 + k)
        ws.cell(row=i, column=2 + k, value=f'=SUMIFS({F("F")},{F("B")},$A{i},{F("H")},{col}$3,{F("E")},"Выбытие")').number_format = MONEY
    ws.cell(row=i, column=6, value=f"=SUM(B{i}:E{i})").number_format = MONEY
tr = 4 + len(CFO)
ws.cell(row=tr, column=1, value="Итого").font = B
for cc in range(2, 7):
    ws.cell(row=tr, column=cc, value=f"=SUM({L(cc)}4:{L(cc)}{tr - 1})").number_format = MONEY
widths(ws, [16, 14, 14, 14, 14, 15])

wb.save(OUT)
print(f"ok {OUT.name}: fact_ops={len(fact)} plan_rows={PLAN_LAST - 1} payments={len(payments)}")
